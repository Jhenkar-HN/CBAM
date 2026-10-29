"""Executive Emissions Passport dashboard and auditable exports."""

from html import escape

import requests
import streamlit as st

from app.modules.calculation.engine import calculate_product_see
from app.modules.reporting.csv_generator import generate_passport_csv
from app.modules.reporting.pdf_generator import generate_passport_pdf
from app.schemas.calculation import (
    DeterministicCalculationRequest,
    ElectricityConsumptionItem,
    FuelCombustionItem,
    PrecursorMaterialItem,
    ProductionAllocationInput,
)
from frontend.ui import inject_custom_css, status_pill

API_BASE_URL = "http://localhost:8000/api/v1"


def gather_effective_inputs() -> DeterministicCalculationRequest:
    """Build deterministic calculation inputs from reviewed session data."""
    ws = st.session_state.get("workspace", {
        "company_name": "Apex Fasteners Pvt Ltd",
        "installation_id": "IN-FDB-001",
        "cn_code": "7318 15 82",
        "includes_indirect": True,
        "target_product_family": "Steel Fasteners (CN 7318 15 82)",
    })
    alloc = st.session_state.get("allocation_data", {
        "target_production_tonnes": 500.0,
        "total_facility_production_tonnes": 625.0,
        "apply_allocation_to_shared_energy": True,
    })
    overrides = st.session_state.get("field_overrides", {})
    docs = st.session_state.get("uploaded_documents", {})

    quantities = {"electricity": 250000.0, "fuel": 15000.0, "precursor": 520.0}
    confidences = {"electricity": 0.96, "fuel": 0.95, "precursor": 0.95}
    for digest, document in docs.items():
        for field in document.get("extracted_fields", []):
            name = str(field.get("field_name", "")).lower()
            key = f"{digest}_{field.get('field_name', '')}"
            effective = overrides.get(key, {}).get("override_value", field.get("extracted_value", 0.0))
            try:
                value = float(effective)
            except (TypeError, ValueError):
                continue
            if "electricity" in name:
                quantities["electricity"] = max(0.0, value)
                confidences["electricity"] = float(field.get("confidence_score", 0.95))
            elif "furnace" in name or "fuel" in name:
                quantities["fuel"] = max(0.001, value)
                confidences["fuel"] = float(field.get("confidence_score", 0.95))
            elif "precursor" in name:
                quantities["precursor"] = max(0.001, value)
                confidences["precursor"] = float(field.get("confidence_score", 0.95))
            elif "production" in name and alloc.get("use_extracted_production"):
                alloc["target_production_tonnes"] = max(0.001, value)

    fuels = [FuelCombustionItem(
        fuel_name="Furnace Oil", quantity=quantities["fuel"], unit="litre",
        ncv=0.0402, ef=0.0774, oxidation_factor=1.0,
        confidence_score=max(0.1, min(1.0, confidences["fuel"])), is_shared_utility=True,
    )]
    electricity = ElectricityConsumptionItem(
        source_name="State Grid / PPA", consumed_quantity=quantities["electricity"], unit="kWh",
        grid_ef_tco2_per_mwh=0.716,
        confidence_score=max(0.1, min(1.0, confidences["electricity"])), is_shared_utility=True,
    )
    precursor = PrecursorMaterialItem(
        material_name="Steel Wire Rod", consumed_quantity=quantities["precursor"], unit="tonne",
        embedded_see_tco2_per_tonne=1.85, source_type="supplier_actual", cn_code="7228 30",
        confidence_score=max(0.1, min(1.0, confidences["precursor"])),
    )
    target = float(alloc.get("target_production_tonnes", 500.0))
    total = max(target, float(alloc.get("total_facility_production_tonnes", 625.0)))
    return DeterministicCalculationRequest(
        reporting_period_id=1,
        cn_code=ws.get("cn_code", "7318 15 82"),
        production=ProductionAllocationInput(
            target_product_family=ws.get("target_product_family", "Steel Fasteners"),
            target_production_quantity=target,
            target_production_unit="tonne",
            total_facility_production_quantity=total,
            total_facility_production_unit="tonne",
        ),
        fuels=fuels,
        electricity=electricity,
        precursors=[precursor],
        apply_allocation_to_shared_energy=alloc.get("apply_allocation_to_shared_energy", True),
        run_monte_carlo=True,
        monte_carlo_iterations=2000,
    )


def _render_confidence_band(uncertainty: dict, unit: str) -> None:
    p5 = float(uncertainty["p5"])
    p50 = float(uncertainty["p50"])
    p95 = float(uncertainty["p95"])
    domain_low = min(p5, p50, p95)
    domain_high = max(p5, p50, p95)
    span = max(domain_high - domain_low, max(abs(domain_high), 1.0) * 0.04)
    domain_low -= span * 0.08
    domain_high += span * 0.08
    domain_span = max(domain_high - domain_low, 1e-9)
    start = max(0.0, min(100.0, (p5 - domain_low) / domain_span * 100))
    end = max(start, min(100.0, (p95 - domain_low) / domain_span * 100))
    median = max(0.0, min(100.0, (p50 - domain_low) / domain_span * 100))
    st.markdown(
        f'<div class="confidence-track"><div class="confidence-range" style="left:{start:.2f}%;width:{end-start:.2f}%"></div>'
        f'<div class="confidence-marker" style="left:{median:.2f}%"></div></div>',
        unsafe_allow_html=True,
    )
    low, mid, high = st.columns(3)
    low.metric("P5 · lower bound", f"{p5:.4f} {unit}")
    mid.metric("P50 · median", f"{p50:.4f} {unit}")
    high.metric("P95 · upper bound", f"{p95:.4f} {unit}")
    st.caption(f"90% simulation interval · {uncertainty.get('iterations', 0):,} iterations")


def render_dashboard_view() -> None:
    inject_custom_css()
    st.title("Emissions Passport")
    st.caption("Executive emissions summary with traceable inputs, deterministic calculations, and uncertainty ranges.")

    ws = st.session_state.get("workspace", {})
    heading, refresh_col = st.columns([5, 1])
    with heading:
        st.markdown(f"**{ws.get('company_name', 'Apex Fasteners')}** · {ws.get('installation_name', 'Installation')} · CN `{ws.get('cn_code', '7318 15 82')}`")
    with refresh_col:
        st.button("Recalculate", type="primary", use_container_width=True, key="passport_recalculate")

    calc_request = gather_effective_inputs()
    with st.expander("Calculation inputs and fallback scenario", expanded=False):
        force_fallback = st.checkbox("Simulate missing supplier precursor SEE using a fallback default", key="force_precursor_fallback")
        if force_fallback and calc_request.precursors:
            item = calc_request.precursors[0]
            item.is_fallback = True
            item.source_type = "eu_default"
            item.embedded_see_tco2_per_tonne = None
            item.fallback_markup_pct = 10.0

    calculation = None
    with st.spinner("Calculating emissions and uncertainty interval…"):
        try:
            response = requests.post(
                f"{API_BASE_URL}/calculations/calculate?save_to_db=true",
                json=calc_request.model_dump(), timeout=5,
            )
            if response.ok:
                calculation = response.json()
            else:
                st.warning(f"Backend calculation returned HTTP {response.status_code}; using the local calculation engine.")
        except requests.RequestException:
            st.caption("Backend unavailable; calculation is running locally and will not be saved to the backend ledger.")

        if calculation is None:
            calculation = calculate_product_see(calc_request).model_dump(mode="json")

    st.session_state["latest_calculation"] = calculation
    see = float(calculation["specific_embedded_emissions_see"])
    quality = str(calculation.get("data_quality_rating", "ACTUAL_PRIMARY"))
    fallback = quality == "FALLBACK_DEFAULT"
    pill_variant = "fallback" if fallback else ("primary" if quality == "ACTUAL_PRIMARY" else "human")
    st.markdown(
        f'{status_pill("DEFAULT FALLBACK USED" if fallback else quality.replace("_", " "), pill_variant)} '
        f'{status_pill("SCOPE 2 INCLUDED" if calculation.get("includes_indirect_delta_cn") else "SCOPE 2 EXEMPT", "neutral")}',
        unsafe_allow_html=True,
    )

    metric_specs = [
        ("Specific embedded emissions", f"{see:.4f}", "tCO₂e / tonne"),
        ("Scope 1 · direct", f"{float(calculation['allocated_scope1_direct_tco2']):,.2f}", "tCO₂"),
        ("Scope 2 · indirect", f"{float(calculation['allocated_scope2_indirect_tco2']):,.2f}", "tCO₂"),
        ("Precursor emissions", f"{float(calculation['precursor_emissions_tco2']):,.2f}", "tCO₂"),
    ]
    metric_cols = st.columns(4)
    for column, (label, value, help_text) in zip(metric_cols, metric_specs):
        with column:
            st.metric(label, value, help=help_text)

    allocation_col, production_col, scope_col = st.columns(3)
    allocation_col.metric("Mass allocation factor · αₚ", f"{float(calculation['allocation_factor_alpha']):.4f}")
    production_col.metric("Net target production", f"{float(calculation['net_target_production_tonnes']):,.2f} t")
    scope_col.metric("Scope 2 treatment", "Included" if calculation.get("includes_indirect_delta_cn") else "Exempt")

    st.markdown("### Statistical uncertainty")
    uncertainty = calculation.get("uncertainty")
    if uncertainty:
        _render_confidence_band(uncertainty, "tCO₂e/t")
    else:
        st.info("No uncertainty distribution was returned for this calculation.")

    st.markdown("### Audit trail and disclosures")
    with st.expander("View calculation formula and component breakdown", expanded=True):
        st.latex(calculation.get("formula_latex", ""))
        breakdown = st.columns(4)
        breakdown[0].metric("Facility Scope 1", f"{float(calculation['facility_gross_scope1_tco2']):,.2f} tCO₂")
        breakdown[1].metric("Allocated Scope 1", f"{float(calculation['allocated_scope1_direct_tco2']):,.2f} tCO₂")
        breakdown[2].metric("Facility Scope 2", f"{float(calculation['facility_gross_scope2_tco2']):,.2f} tCO₂")
        breakdown[3].metric("Total embedded emissions", f"{float(calculation['total_embedded_emissions_tco2']):,.2f} tCO₂")
        st.json(calculation.get("input_snapshot", {}))

    fallback_notes = calculation.get("fallback_notes") or []
    if fallback_notes or fallback:
        notes = "<br>".join(escape(str(note)) for note in fallback_notes) or "Fallback assumptions were applied to precursor emissions; review the selected official default and policy markup."
        st.markdown(f'<div class="fallback-callout"><b>Fallback disclosure</b><br>{notes}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="legal-callout"><b>Decision-support prototype.</b> This report does not certify emissions or replace an accredited verifier.</div>',
        unsafe_allow_html=True,
    )

    export_payload = {
        "workspace": ws,
        "calculation": calculation,
        "uploaded_documents": st.session_state.get("uploaded_documents", {}),
    }
    pdf_bytes = generate_passport_pdf(export_payload)
    csv_text = generate_passport_csv(export_payload)
    cn_filename = str(ws.get("cn_code", "7318")).replace(" ", "_")
    st.markdown("### Download evidence pack")
    pdf_col, csv_col = st.columns(2)
    with pdf_col:
        st.download_button(
            "Download Emissions Passport · PDF", data=pdf_bytes,
            file_name=f"CBAM_Emissions_Passport_{cn_filename}.pdf",
            mime="application/pdf", type="primary", use_container_width=True,
        )
    with csv_col:
        st.download_button(
            "Download Evidence Ledger · CSV", data=csv_text.encode("utf-8"),
            file_name=f"CBAM_Audit_Evidence_Ledger_{cn_filename}.csv",
            mime="text/csv", use_container_width=True,
        )
