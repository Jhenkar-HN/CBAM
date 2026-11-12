"""Workspace setup based on information supplied by the operator."""

from datetime import date

import streamlit as st

from app.db.database import SessionLocal
from app.modules.calculation.factors import list_cn_codes


def render_workspace_view() -> None:
    st.subheader("Workspace & product setup")
    st.caption("Enter installation details and select the CN code that matches your exported product.")

    ws = st.session_state.get("workspace", {})
    with SessionLocal() as db:
        cn_rows = list_cn_codes(db)
    cn_codes = [row["cn_code"] for row in cn_rows if row["sector"] != "Iron and Steel (Precursor)"]
    descriptions = {row["cn_code"]: row["description"] for row in cn_rows}

    with st.form("workspace_setup"):
        company_name = st.text_input("Exporting company name", value=ws.get("company_name", ""))
        installation_name = st.text_input("Installation / factory name", value=ws.get("installation_name", ""))
        installation_id = st.text_input("Installation ID or UN/LOCODE", value=ws.get("installation_id", ""))
        country = st.text_input("Country of origin", value=ws.get("country", ""), placeholder="Enter the actual country")
        cn_options = [""] + cn_codes
        old_code = ws.get("cn_code", "")
        selected_code = st.selectbox(
            "Target product CN code",
            cn_options,
            index=cn_options.index(old_code) if old_code in cn_options else 0,
            format_func=lambda code: "Select a CN code" if not code else f"{code} · {descriptions.get(code, '')}",
        )
        start_text = st.text_input("Reporting period start (YYYY-MM-DD)", value=str(ws.get("start_date", "")))
        end_text = st.text_input("Reporting period end (YYYY-MM-DD)", value=str(ws.get("end_date", "")))
        save = st.form_submit_button("Save workspace", type="primary", use_container_width=True)

    if save:
        missing = [label for label, value in (
            ("company name", company_name), ("installation name", installation_name),
            ("installation ID", installation_id), ("country", country), ("CN code", selected_code),
            ("reporting period start", start_text), ("reporting period end", end_text),
        ) if not value.strip()]
        try:
            start_date = date.fromisoformat(start_text.strip())
            end_date = date.fromisoformat(end_text.strip())
            if start_date > end_date:
                raise ValueError("Reporting period start must be on or before its end.")
        except ValueError as exc:
            st.error(str(exc) or "Enter reporting dates in YYYY-MM-DD format.")
            return
        if missing:
            st.error("Complete these workspace fields using your actual records: " + ", ".join(missing))
            return

        cn_row = next(row for row in cn_rows if row["cn_code"] == selected_code)
        st.session_state["workspace"] = {
            "company_name": company_name.strip(),
            "installation_name": installation_name.strip(),
            "installation_id": installation_id.strip(),
            "un_locode": installation_id.strip(),
            "country": country.strip(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "reporting_period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "cn_code": selected_code,
            "includes_indirect": cn_row["includes_indirect_emissions"],
            "requires_precursors": cn_row["requires_precursors"],
            "target_product_family": f"{descriptions[selected_code]} (CN {selected_code})",
        }
        st.success("Workspace saved from the details you entered.")
