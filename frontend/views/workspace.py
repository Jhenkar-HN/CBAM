"""Workspace & Product Setup View."""

import streamlit as st
from datetime import date

CN_CODE_OPTIONS = {
    "7318 15 82": {
        "desc": "Other screws and bolts, of steel, without heads or with cold formed heads",
        "sector": "Iron and Steel",
        "delta_cn": True,
        "requires_precursors": True,
        "precursor_name": "Steel Wire Rod (Alloy / Non-alloy)",
    },
    "7318 15 95": {
        "desc": "Other screws and bolts, of steel, with heads, tensile strength < 800 MPa",
        "sector": "Iron and Steel",
        "delta_cn": True,
        "requires_precursors": True,
        "precursor_name": "Steel Wire Rod (Alloy / Non-alloy)",
    },
    "7318 16 00": {
        "desc": "Nuts, of steel",
        "sector": "Iron and Steel",
        "delta_cn": True,
        "requires_precursors": True,
        "precursor_name": "Steel Wire Rod / Hex Bars",
    },
    "7228 30 00": {
        "desc": "Precursor: Other bars and rods of alloy steel; wire rod",
        "sector": "Iron and Steel (Precursor)",
        "delta_cn": True,
        "requires_precursors": False,
        "precursor_name": "Direct Crude Steel / Billets",
    },
}


def render_workspace_view():
    st.subheader("🏢 Workspace & Product Setup")
    st.caption("Configure manufacturing installation metadata, reporting period, and EU CBAM covered CN codes.")

    # Initialize session state for workspace if not present
    if "workspace" not in st.session_state:
        st.session_state["workspace"] = {
            "company_name": "Apex Fasteners Pvt Ltd",
            "installation_name": "Apex Unit 1 - Cold Forging Plant",
            "installation_id": "IN-FDB-001",
            "un_locode": "IN FDB",
            "country": "India",
            "reporting_period": "2026 (Annual)",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "cn_code": "7318 15 82",
            "includes_indirect": True,
            "requires_precursors": True,
        }

    ws = st.session_state["workspace"]

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Exporting Company Name", value=ws["company_name"])
            installation_name = st.text_input("Installation / Factory Name", value=ws["installation_name"])
            installation_id = st.text_input("Installation UN/LOCODE or Local ID", value=ws["installation_id"])

        with col2:
            country = st.selectbox("Country of Origin", ["India", "Vietnam", "Turkey", "Other"], index=0)
            rep_col1, rep_col2 = st.columns(2)
            with rep_col1:
                start_date = st.date_input("Reporting Period Start", value=ws["start_date"])
            with rep_col2:
                end_date = st.date_input("Reporting Period End", value=ws["end_date"])

        st.markdown("---")
        st.markdown("#### 🎯 EU Combined Nomenclature (CN) Product Classification")

        cn_selection = st.selectbox(
            "Target Product CN Code (8-digit)",
            options=list(CN_CODE_OPTIONS.keys()),
            format_func=lambda x: f"{x} - {CN_CODE_OPTIONS[x]['desc'][:65]}...",
            index=list(CN_CODE_OPTIONS.keys()).index(ws["cn_code"]) if ws["cn_code"] in CN_CODE_OPTIONS else 0,
        )

        selected_meta = CN_CODE_OPTIONS[cn_selection]

        c_info1, c_info2, c_info3 = st.columns(3)
        with c_info1:
            st.info(f"**Sector:** {selected_meta['sector']}")
        with c_info2:
            st.info(f"**Precursor Mandatory:** {'Yes' if selected_meta['requires_precursors'] else 'No'}")
        with c_info3:
            st.info(f"**Default Material:** {selected_meta['precursor_name']}")

        # Toggle for Scope 2
        scope2_included = st.toggle(
            "Include Indirect Emissions (Scope 2 / delta_CN = 1)",
            value=selected_meta["delta_cn"],
            help="Under the EU CBAM definitive regime, covered steel goods must embed Scope 2 electricity unless explicitly exempt by regulation.",
        )

        if st.button("💾 Save Workspace Configuration", type="primary", use_container_width=True):
            st.session_state["workspace"] = {
                "company_name": company_name,
                "installation_name": installation_name,
                "installation_id": installation_id,
                "un_locode": installation_id,
                "country": country,
                "reporting_period": f"{start_date.year} (CBAM Definitive)",
                "start_date": start_date,
                "end_date": end_date,
                "cn_code": cn_selection,
                "includes_indirect": scope2_included,
                "requires_precursors": selected_meta["requires_precursors"],
                "target_product_family": f"Fasteners ({cn_selection})",
            }
            st.success("✅ Workspace configuration saved successfully!")
