"""Multi-Format Upload & Ingestion View."""

import pandas as pd
import requests
import streamlit as st
from app.modules.document_ai.extractor import run_document_ai_extraction
from frontend.ui import empty_state, page_header

API_BASE_URL = "http://localhost:8000/api/v1"


def render_upload_view():
    page_header(
        "Step 2 of 5",
        "Upload source records",
        "Upload factory invoices, power bills, mill certificates, and weighbridge logs. "
        "Each file is fingerprinted with SHA-256 so every number can be traced back to its source.",
    )

    if "uploaded_documents" not in st.session_state:
        st.session_state["uploaded_documents"] = {}

    workspace = st.session_state.get("workspace")
    if not workspace:
        empty_state("🏭", "Workspace not set up yet", "Save the company and installation details in step 1 before uploading records.")
        return

    # File uploader
    uploaded_files = st.file_uploader(
        "Business records · PDF, scanned image, CSV or Excel",
        type=["pdf", "png", "jpg", "jpeg", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    # Ingestion button
    if uploaded_files:
        ingested_new = False
        for file_obj in uploaded_files:
            file_bytes = file_obj.getvalue()
            filename = file_obj.name

            # Check if already processed
            already_processed = any(
                doc.get("filename") == filename
                for doc in st.session_state["uploaded_documents"].values()
            )

            if not already_processed:
                with st.spinner(f"Ingesting & extracting: {filename}..."):
                    extraction_data = None

                    # 1. Try FastAPI endpoint
                    try:
                        files = {"file": (filename, file_bytes, file_obj.type or "application/octet-stream")}
                        data = {"workspace_id": workspace["installation_id"]}
                        resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files, data=data, timeout=5)
                        if resp.status_code == 201:
                            extraction_data = resp.json()
                    except Exception:
                        pass

                    # 2. Local fallback if API is not running as a daemon
                    if not extraction_data:
                        result_obj = run_document_ai_extraction(file_bytes, filename)
                        extraction_data = result_obj.model_dump()

                    # Save to session state
                    doc_hash = extraction_data["document_hash"]
                    st.session_state["uploaded_documents"][doc_hash] = {
                        "filename": filename,
                        "document_hash": doc_hash,
                        "file_size_bytes": len(file_bytes),
                        "page_count": extraction_data.get("page_count", 1),
                        "extracted_fields": extraction_data.get("extracted_fields", []),
                    }
                    st.toast(f"Parsed {filename}", icon="✅")
                    ingested_new = True
        if ingested_new:
            # Rerun so the sidebar counter and step checkmarks reflect the new ledger entries.
            st.rerun()

    # Ingestion Manifest / Ledger Table
    docs = st.session_state["uploaded_documents"]
    if docs:
        total_fields = sum(len(doc["extracted_fields"]) for doc in docs.values())
        st.markdown("### Document ledger")
        summary = st.columns(3)
        summary[0].metric("Documents", len(docs))
        summary[1].metric("Candidate fields", total_fields)
        summary[2].metric("Total size", f"{sum(doc['file_size_bytes'] for doc in docs.values()) / 1024:,.1f} KB")
        for doc_hash, doc in docs.items():
            with st.expander(f"📄 {doc['filename']} · {doc['file_size_bytes'] / 1024:.1f} KB · {len(doc['extracted_fields'])} fields", expanded=len(docs) == 1):
                st.markdown('<div class="meta-label">SHA-256 fingerprint</div>', unsafe_allow_html=True)
                st.code(doc["document_hash"], language=None)

                if doc["extracted_fields"]:
                    st.markdown('<div class="meta-label">Extracted candidates</div>', unsafe_allow_html=True)
                    table_rows = []
                    for f in doc["extracted_fields"]:
                        table_rows.append({
                            "Field Name": f["field_name"],
                            "Quantity": f"{float(f['extracted_value']):,.4f}".rstrip("0").rstrip("."),
                            "Unit": f["unit"],
                            "Confidence": f"{f['confidence_score'] * 100:.0f}%",
                            "Page": f["evidence_page"],
                            "Verbatim Snippet": f["evidence_snippet"],
                        })
                    st.table(pd.DataFrame(table_rows).style.hide(axis="index"))
                else:
                    st.info("No numerical activity candidates identified in this file.")
        st.caption("Next: check each extracted value against its evidence in step 3.")

    else:
        empty_state("📄", "No documents yet", "Drop your factory electricity bills, fuel receipts, supplier certificates, or production sheets above.")
