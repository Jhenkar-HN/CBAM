"""Evidence inspector and field-level human override review."""

from datetime import datetime
from html import escape

import requests
import streamlit as st

from frontend.ui import inject_custom_css, status_pill

API_BASE_URL = "http://localhost:8000/api/v1"


def _confidence_label(score: float) -> tuple[str, str]:
    percentage = max(0, min(100, round(score * 100)))
    if percentage >= 90:
        return f"High · {percentage}% confidence", "primary"
    if percentage >= 70:
        return f"Medium · {percentage}% confidence", "human"
    return f"Low · {percentage}% confidence", "fallback"


def render_review_view() -> None:
    inject_custom_css()
    st.title("Extraction review")
    st.caption("Inspect each candidate against its source evidence. Corrections are recorded with the reviewer and justification.")

    docs = st.session_state.get("uploaded_documents", {})
    if not docs:
        st.info("No documents are available yet. Upload a source record to begin review.")
        return

    overrides = st.session_state.setdefault("field_overrides", {})
    doc_options = {
        digest: f"{document.get('filename', 'Document')} · SHA-256 {digest[:12]}…"
        for digest, document in docs.items()
    }
    selected_hash = st.selectbox(
        "Source document",
        options=list(doc_options),
        format_func=lambda digest: doc_options[digest],
        key="review_selected_document",
    )
    selected_doc = docs[selected_hash]
    fields = selected_doc.get("extracted_fields", [])

    with st.container(border=True):
        left, right, third = st.columns([2, 1, 2])
        with left:
            st.markdown('<div class="meta-label">File</div>', unsafe_allow_html=True)
            st.write(selected_doc.get("filename", "Unnamed document"))
        with right:
            st.markdown('<div class="meta-label">Evidence fields</div>', unsafe_allow_html=True)
            st.write(str(len(fields)))
        with third:
            st.markdown('<div class="meta-label">SHA-256</div>', unsafe_allow_html=True)
            st.code(selected_hash, language=None)

    if not fields:
        st.warning("No activity fields were extracted from this file. Check the document quality or enter source data through the supported workflow.")
        return

    st.markdown("### Candidate fields")
    for index, field in enumerate(fields):
        field_name = str(field.get("field_name", f"field_{index + 1}"))
        raw_value = float(field.get("extracted_value", 0.0))
        raw_unit = str(field.get("unit", ""))
        override_key = f"{selected_hash}_{field_name}"
        current = overrides.get(override_key)
        confidence, confidence_variant = _confidence_label(float(field.get("confidence_score", 0.0)))

        with st.container(border=True):
            evidence_col, form_col = st.columns([1, 1], gap="large")
            with evidence_col:
                st.markdown(f"#### {field_name.replace('_', ' ').title()}")
                st.markdown(status_pill(confidence, confidence_variant), unsafe_allow_html=True)
                st.caption(f"Page {field.get('evidence_page', 1)} · Source: {selected_doc.get('filename', 'document')}")
                snippet = escape(str(field.get("evidence_snippet") or "No source snippet was captured."))
                st.markdown(f'<div class="evidence-box">{snippet}</div>', unsafe_allow_html=True)

                if current:
                    raw_display = f"{current.get('raw_value', raw_value):,.2f} {current.get('raw_unit', raw_unit)}"
                    effective_display = f"{current['override_value']:,.2f} {current.get('override_unit', raw_unit)}"
                    st.markdown(
                        f'<div class="diff-box"><b>Raw:</b> {escape(raw_display)} &nbsp;→&nbsp; '
                        f'<b>Effective:</b> {escape(effective_display)}<br>'
                        f'<small>Reviewer: {escape(current.get("user_id", "Reviewer"))} · '
                        f'{escape(current.get("updated_at", ""))}</small></div>',
                        unsafe_allow_html=True,
                    )
                    if not current.get("api_synced", False):
                        st.caption("This override is active for this session but has not synced to the backend audit ledger.")
                    else:
                        st.markdown(status_pill("HUMAN OVERRIDDEN", "human"), unsafe_allow_html=True)
                else:
                    st.markdown(status_pill("AI EXTRACTED · UNEDITED", "primary"), unsafe_allow_html=True)

            with form_col:
                st.markdown("#### Review value")
                with st.form(key=f"override_form_{index}_{selected_hash[:12]}_{field_name}"):
                    value = st.number_input(
                        "Quantity",
                        value=float(current["override_value"]) if current else raw_value,
                        format="%.4f",
                        key=f"value_{index}_{selected_hash[:12]}_{field_name}",
                    )
                    unit = st.text_input(
                        "Unit",
                        value=str(current.get("override_unit", raw_unit)) if current else raw_unit,
                        key=f"unit_{index}_{selected_hash[:12]}_{field_name}",
                    )
                    reason = st.text_area(
                        "Justification",
                        value=str(current.get("override_reason", "")) if current else "",
                        placeholder="Required when changing the extracted value or unit.",
                        key=f"reason_{index}_{selected_hash[:12]}_{field_name}",
                        height=90,
                    )
                    reviewer = st.text_input(
                        "Reviewer ID",
                        value=str(current.get("user_id", "")) if current else "",
                        placeholder="Enter your name or reviewer ID",
                        key=f"reviewer_{index}_{selected_hash[:12]}_{field_name}",
                    )
                    save = st.form_submit_button("Save audit override", type="primary", use_container_width=True)

                if save:
                    changed = value != raw_value or unit.strip() != raw_unit
                    if not changed:
                        st.info("The value matches the extracted candidate; it remains labeled AI Extracted.")
                    elif not reason.strip():
                        st.error("Add a justification before saving a changed value or unit.")
                    elif not reviewer.strip():
                        st.error("Enter a reviewer ID to identify the person making the correction.")
                    else:
                        payload = {
                            "document_hash": selected_hash,
                            "field_name": field_name,
                            "override_value": value,
                            "override_unit": unit.strip(),
                            "override_reason": reason.strip(),
                            "user_id": reviewer.strip(),
                        }
                        synced = False
                        sync_message = ""
                        try:
                            response = requests.post(f"{API_BASE_URL}/documents/override", json=payload, timeout=5)
                            if response.ok:
                                synced = True
                            else:
                                sync_message = f"Backend returned HTTP {response.status_code}."
                        except requests.RequestException as exc:
                            sync_message = str(exc)

                        overrides[override_key] = {
                            **payload,
                            "raw_value": raw_value,
                            "raw_unit": raw_unit,
                            "api_synced": synced,
                            "updated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
                        }
                        if synced:
                            st.success("Override saved to the backend audit ledger and applied to the current calculation inputs.")
                        else:
                            st.warning(f"Override is active for this session, but backend sync failed: {sync_message}")
                        st.rerun()
