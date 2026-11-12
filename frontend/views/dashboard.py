"""Executive Emissions Passport dashboard and auditable exports."""

from html import escape

import requests
import streamlit as st

from app.modules.calculation.engine import calculate_product_see
from app.db.database import SessionLocal
from app.modules.calculation.factors import list_cn_codes, list_factors
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
    """Build inputs only from reviewed uploaded fields and operator-entered production data."""
    ws = st.session_state.get("workspace") or {}
    alloc = st.session_state.get("allocation_data") or {}
    docs = st.session_state.get("uploaded_documents") or {}
    overrides = st.session_state.get("field_overrides") or {}
    extracted = []
    for digest, document in docs.items():
        for field in document.get("extracted_fields", []):
            name = str(field.get("field_name", "")).lower()
            key = f"{digest}_{field.get('field_name', '')}"
            override = overrides.get(key) or {}
            raw_value = field.get("extracted_value")
            value = override.get("override_value", raw_value)
            unit = override.get("override_unit") or field.get("unit")
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            extracted.append((name, value, str(unit or ""), float(field.get("confidence_score", 0.0))))

    electricity_field = next((row for row in extracted if "electric" in row[0] or "kwh" in row[0] or "mwh" in row[0]), None)
    fuel_field = next((row for row in extracted if "fuel" in row[0] or "diesel" in row[0] or "gas" in row[0] or "oil" in row[0]), None)
    precursor_field = next((row for row in extracted if any(token in row[0] for token in ("precursor", "wire_rod", "material_quantity")) and not any(token in row[0] for token in ("see", "factor", "emission"))), None)
    precursor_see_field = next((row for row in extracted if any(token in row[0] for token in ("precursor", "wire_rod", "material")) and any(token in row[0] for token in ("see", "factor", "emission"))), None)

    missing = []
    if not ws.get("company_name") or not ws.get("cn_code"):
        missing.append("saved company and product workspace")
    if not alloc.get("target_production_tonnes") or not alloc.get("total_facility_production_tonnes"):
        missing.append("target and total production quantities")
    if alloc.get("fuel_allocation_basis") not in {"shared", "product_only"}:
        missing.append("fuel allocation basis from the meter / invoice")
    if alloc.get("electricity_allocation_basis") not in {"shared", "product_only"}:
        missing.append("electricity allocation basis from the meter / invoice")
    if electricity_field is None:
        missing.append("electricity consumption extracted from an uploaded record")
    if fuel_field is None:
        missing.append("fuel consumption extracted from an uploaded record")
    if precursor_field is None:
        missing.append("precursor quantity extracted from a supplier record")
    if missing:
        raise ValueError("Calculation is unavailable until these actual inputs are provided: " + "; ".join(missing) + ".")

    with SessionLocal() as db:
        factors = list_factors(db)
    fuel_options = factors["fuel"]
    if not fuel_options:
        raise ValueError("No sourced fuel factors are available in the reference database.")
    selected_fuel = st.session_state.get("selected_fuel_factor")
    fuel_names = [item["item_name"] for item in fuel_options]
    if selected_fuel not in fuel_names:
        raise ValueError("Select the fuel type shown on your uploaded fuel record before calculating.")

    electricity_options = factors["electricity"]
    if not electricity_options:
        raise ValueError("No sourced electricity factors are available in the reference database.")
    selected_grid = st.session_state.get("selected_grid_factor")
    grid_names = [item["item_name"] for item in electricity_options]
    if selected_grid not in grid_names:
        raise ValueError("Select the electricity factor that applies to the uploaded electricity record.")

    precursor_code = st.session_state.get("precursor_cn_code")
    if not precursor_code:
        raise ValueError("Select the precursor CN code from the supplier record.")
    precursor_material_name = str(st.session_state.get("precursor_material_name", "")).strip()
    precursor_country = str(st.session_state.get("precursor_country", "")).strip()
    if not precursor_material_name or not precursor_country:
        raise ValueError("Enter the precursor material name and country of origin exactly as shown on the supplier record.")

    fuels = [FuelCombustionItem(
        fuel_name=selected_fuel, quantity=fuel_field[1], unit=fuel_field[2],
        confidence_score=max(0.1, min(1.0, fuel_field[3])),
        is_shared_utility=alloc["fuel_allocation_basis"] == "shared",
    )]
    electricity = ElectricityConsumptionItem(
        source_name=selected_grid, consumed_quantity=electricity_field[1], unit=electricity_field[2],
        confidence_score=max(0.1, min(1.0, electricity_field[3])),
        is_shared_utility=alloc["electricity_allocation_basis"] == "shared",
    )
    supplier_see = precursor_see_field[1] if precursor_see_field else None
    if supplier_see is None:
        raise ValueError("A supplier-declared precursor SEE is missing. Upload supplier emissions data; calculation is blocked without it.")
    precursor = PrecursorMaterialItem(
        material_name=precursor_material_name,
        consumed_quantity=precursor_field[1], unit=precursor_field[2],
        embedded_see_tco2_per_tonne=supplier_see,
        source_type="supplier_actual",
        cn_code=precursor_code,
        country_of_origin=precursor_country,
        confidence_score=max(0.1, min(1.0, precursor_see_field[3] if precursor_see_field else precursor_field[3])),
        is_fallback=False,
    )
    target = float(alloc["target_production_tonnes"])
    total = float(alloc["total_facility_production_tonnes"])
    return DeterministicCalculationRequest(
        reporting_period_id=0,
        cn_code=ws["cn_code"],
        production=ProductionAllocationInput(
            target_product_family=ws["target_product_family"],
            target_production_quantity=target,
            target_production_unit="tonne",
            total_facility_production_quantity=total,
            total_facility_production_unit="tonne",
        ),
        fuels=fuels,
        electricity=electricity,
        precursors=[precursor],
        apply_allocation_to_shared_energy=alloc["apply_allocation_to_shared_energy"],
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
    if not ws.get("company_name") or not ws.get("cn_code"):
        st.info("Complete and save the workspace before calculating.")
        return
    if str(ws.get("country", "")).strip().lower() != "india":
        st.info("The sourced grid-factor registry in this pilot covers India only. No calculation was run for this country.")
        return

    heading, refresh_col = st.columns([5, 1])
    with heading:
        st.markdown(f"**{ws['company_name']}** · {ws.get('installation_name', '')} · CN `{ws['cn_code']}`")
    with refresh_col:
        st.button("Recalculate", type="primary", use_container_width=True, key="passport_recalculate")

    with SessionLocal() as db:
        reference = list_factors(db)
        cn_rows = list_cn_codes(db)
    fuel_rows = reference["fuel"]
    grid_rows = reference["electricity"]
    precursor_codes = [row["cn_code"] for row in cn_rows if "precursor" in row["sector"].lower()]
    if not fuel_rows or not grid_rows:
        st.error("Sourced emission factor reference data is unavailable. No calculation was run.")
        return
    st.markdown("### Reference factors")
    fuel_names = [row["item_name"] for row in fuel_rows]
    grid_names = [row["item_name"] for row in grid_rows]
    factor_col1, factor_col2, factor_col3 = st.columns(3)
    with factor_col1:
        st.selectbox("Fuel type shown on your record", [""] + fuel_names, format_func=lambda value: value or "Select a fuel type", key="selected_fuel_factor")
    with factor_col2:
        st.selectbox("Electricity factor", [""] + grid_names, format_func=lambda value: value or "Select an applicable factor", key="selected_grid_factor")
        grid = next((row for row in grid_rows if row["item_name"] == st.session_state.get("selected_grid_factor")), None)
        if grid:
            st.caption(f"Source: {grid['source_reference']} · {grid['ef_value']} {grid['ef_unit']}")
    with factor_col3:
        if not precursor_codes:
            st.error("No sourced precursor defaults are available.")
            return
        st.selectbox("Precursor CN code", [""] + precursor_codes, format_func=lambda value: value or "Select the code from the supplier record", key="precursor_cn_code")
        st.text_input("Precursor material name (from supplier record)", key="precursor_material_name", placeholder="Use the supplier's material name")
        st.text_input("Precursor country of origin", key="precursor_country", placeholder="Country shown on supplier record")
    st.caption("Supplier SEE must come from the supplier's actual emissions statement; the app will not substitute benchmark values.")

    try:
        calc_request = gather_effective_inputs()
    except ValueError as exc:
        st.info(str(exc))
        st.caption("Upload the source documents, review extracted values, and enter production quantities before requesting a passport calculation.")
        return

    calculation = None
    with st.spinner("Calculating emissions and uncertainty interval…"):
        try:
            response = requests.post(
                f"{API_BASE_URL}/calculations/calculate?save_to_db=false",
                json=calc_request.model_dump(), timeout=5,
            )
            if response.ok:
                calculation = response.json()
            else:
                st.warning(f"Backend calculation returned HTTP {response.status_code}; using the local calculation engine.")
        except requests.RequestException:
            st.caption("Backend unavailable; calculation is running locally and will not be saved to the backend ledger.")

        if calculation is None:
            try:
                with SessionLocal() as db:
                    calculation = calculate_product_see(calc_request, db=db).model_dump(mode="json")
            except ValueError as exc:
                st.error(f"Calculation could not be completed: {exc}")
                return

    st.session_state["latest_calculation"] = calculation
    see = float(calculation["specific_embedded_emissions_see"])
    quality = str(calculation.get("data_quality_rating", "UNKNOWN"))
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
        "overrides": st.session_state.get("field_overrides", {}),
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
