"""Deterministic CBAM Specific Embedded Emissions (SEE) Calculation Engine.

STRICT PRINCIPLE: AI NEVER PERFORMS EMISSIONS ARITHMETIC.
All calculations are 100% deterministic, testable, and auditable.

Every emission factor and CN classification is resolved from the seeded
reference tables. The engine contains no fallback factor values of its own:
if a required factor is missing it raises, rather than inventing data.
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.modules.calculation.factors import (
    find_cn_code,
    resolve_electricity_factor,
    resolve_fuel_factors,
    resolve_precursor_default,
)
from app.modules.calculation.unit_converter import (
    to_energy_gigajoules,
    to_megawatt_hours,
    to_metric_tonnes,
)
from app.schemas.calculation import (
    DataQualityRating,
    DeterministicCalculationRequest,
    DeterministicCalculationResult,
    ElectricityConsumptionItem,
    FuelCombustionItem,
    PrecursorMaterialItem,
)


def compute_mass_allocation_factor(
    target_production_tonnes: float,
    total_facility_production_tonnes: float,
) -> float:
    """
    Calculates multi-product mass allocation factor alpha_p:
    alpha_p = Net Target Production / Total Facility Production
    """
    if target_production_tonnes <= 0:
        raise ValueError(f"Target production quantity must be greater than 0, got {target_production_tonnes}")
    if total_facility_production_tonnes <= 0:
        raise ValueError(f"Total facility production quantity must be greater than 0, got {total_facility_production_tonnes}")
    if target_production_tonnes > total_facility_production_tonnes:
        raise ValueError(
            f"Target production quantity ({target_production_tonnes} t) cannot exceed "
            f"total facility production quantity ({total_facility_production_tonnes} t)."
        )

    return target_production_tonnes / total_facility_production_tonnes


def determine_delta_cn(cn_code: str, db: Session) -> bool:
    """
    Determines whether the CN code requires Scope 2 indirect emissions (delta_CN = 1)
    using the CBAM CN code registry.
    """
    if db is None:
        raise ValueError("A database session is required to resolve the CBAM CN classification.")
    entry = find_cn_code(db, cn_code)
    if entry is None:
        raise ValueError(
            f"CN code '{cn_code}' is not registered as a CBAM-covered good. "
            "Select a CN code from the reference registry."
        )
    return bool(entry.includes_indirect_emissions)


def _resolve_request_factors(
    request: DeterministicCalculationRequest,
    db: Session,
) -> Tuple[DeterministicCalculationRequest, List[str]]:
    """Fills missing factor values from the reference database, or raises."""
    if db is None:
        raise ValueError("A database session is required to resolve emission factors.")

    notes: List[str] = []

    fuels: List[FuelCombustionItem] = []
    for fuel in request.fuels:
        ncv = fuel.ncv
        ef = fuel.ef
        if ncv is None or ncv <= 0 or ef is None or ef <= 0:
            row = resolve_fuel_factors(db, fuel.fuel_name)
            if row is None or row.ncv_value is None or row.ef_value is None:
                raise ValueError(
                    f"No reference NCV/EF found for fuel '{fuel.fuel_name}'. "
                    "Select a fuel from the reference factor list."
                )
            if ncv is None or ncv <= 0:
                ncv = row.ncv_value
                notes.append(f"Resolved NCV for {fuel.fuel_name} from '{row.item_name}': {ncv} {row.ncv_unit}.")
            if ef is None or ef <= 0:
                ef = row.ef_value
                notes.append(f"Resolved EF for {fuel.fuel_name} from '{row.item_name}': {ef} {row.ef_unit}.")
        fuels.append(fuel.model_copy(update={"ncv": ncv, "ef": ef}))

    electricity = request.electricity
    if electricity is not None and (electricity.grid_ef_tco2_per_mwh is None or electricity.grid_ef_tco2_per_mwh <= 0):
        row = resolve_electricity_factor(db, electricity.source_name)
        if row is None or row.ef_value is None:
            raise ValueError(
                f"No reference electricity factor matched '{electricity.source_name}'. "
                "Select an electricity factor from the reference list."
            )
        electricity = electricity.model_copy(update={"grid_ef_tco2_per_mwh": row.ef_value})
        notes.append(
            f"Resolved grid EF for {electricity.source_name} from '{row.item_name}': {row.ef_value} {row.ef_unit}."
        )

    precursors: List[PrecursorMaterialItem] = []
    for prec in request.precursors:
        is_fallback = prec.is_fallback or prec.source_type == "eu_default"
        if not is_fallback:
            if prec.embedded_see_tco2_per_tonne is None or prec.embedded_see_tco2_per_tonne <= 0:
                raise ValueError(
                    f"Supplier SEE is required for precursor '{prec.material_name}' (CN {prec.cn_code}). "
                    "Upload supplier emissions data or explicitly mark an approved official fallback."
                )
            precursors.append(prec)
            continue

        row = resolve_precursor_default(db, prec.cn_code)
        if row is None or row.ef_value is None:
            raise ValueError(
                f"No EU default precursor factor is registered for CN code '{prec.cn_code}'. "
                "Provide a supplier-declared SEE or select a registered default."
            )
        markup_pct = prec.fallback_markup_pct
        if markup_pct is None:
            markup_pct = row.markup_pct
        if markup_pct is None:
            raise ValueError(
                f"Reference precursor factor '{row.item_name}' has no regulatory markup percentage configured."
            )
        see_val = row.ef_value * (1.0 + (markup_pct / 100.0))
        notes.append(
            f"Precursor '{prec.material_name}' (CN {prec.cn_code}): applied reference default SEE of "
            f"{row.ef_value} tCO2/t from '{row.item_name}' with +{markup_pct}% penalty markup -> {see_val:.4f} tCO2/t."
        )
        precursors.append(
            prec.model_copy(
                update={
                    "embedded_see_tco2_per_tonne": see_val,
                    "fallback_markup_pct": markup_pct,
                    "is_fallback": True,
                }
            )
        )

    resolved = request.model_copy(
        update={
            "fuels": fuels,
            "electricity": electricity,
            "precursors": precursors,
        }
    )
    return resolved, notes


def calculate_fuel_emissions(
    fuel: FuelCombustionItem,
    allocation_factor_alpha: float,
    apply_allocation: bool = True,
) -> Tuple[float, float, List[str]]:
    """
    Calculates direct emissions from a single fuel source.
    Direct = Quantity * NCV * EF * OF
    Returns: (gross_emissions_tco2, allocated_emissions_tco2, notes)
    """
    if fuel.ncv is None or fuel.ncv <= 0:
        raise ValueError(f"Missing Net Calorific Value (NCV) for fuel '{fuel.fuel_name}'.")
    if fuel.ef is None or fuel.ef <= 0:
        raise ValueError(f"Missing Emission Factor (EF) for fuel '{fuel.fuel_name}'.")

    of = fuel.oxidation_factor if fuel.oxidation_factor is not None else 1.0

    energy_gj = to_energy_gigajoules(fuel.quantity, fuel.unit, fuel.ncv)
    gross_tco2 = energy_gj * fuel.ef * of

    if apply_allocation and fuel.is_shared_utility:
        allocated_tco2 = gross_tco2 * allocation_factor_alpha
    else:
        allocated_tco2 = gross_tco2

    return gross_tco2, allocated_tco2, []


def calculate_electricity_emissions(
    electricity_item: ElectricityConsumptionItem,
    allocation_factor_alpha: float,
    apply_allocation: bool = True,
) -> Tuple[float, float, List[str]]:
    """
    Calculates indirect emissions from grid / PPA electricity consumption.
    Indirect = Consumed MWh * Grid EF (tCO2/MWh)
    Returns: (gross_emissions_tco2, allocated_emissions_tco2, notes)
    """
    if not electricity_item or electricity_item.consumed_quantity <= 0:
        return 0.0, 0.0, []

    grid_ef = electricity_item.grid_ef_tco2_per_mwh
    if grid_ef is None or grid_ef <= 0:
        raise ValueError(
            f"Missing grid emission factor for electricity source '{electricity_item.source_name}'."
        )

    mwh = to_megawatt_hours(electricity_item.consumed_quantity, electricity_item.unit)
    gross_tco2 = mwh * grid_ef

    if apply_allocation and electricity_item.is_shared_utility:
        allocated_tco2 = gross_tco2 * allocation_factor_alpha
    else:
        allocated_tco2 = gross_tco2

    return gross_tco2, allocated_tco2, []


def calculate_precursor_emissions(
    precursor: PrecursorMaterialItem,
) -> Tuple[float, bool, List[str]]:
    """
    Calculates embedded emissions from a precursor material.
    Emissions = Mass (tonnes) * Embedded SEE (tCO2/tonne)
    Returns: (precursor_tco2, is_fallback_used, notes)
    """
    is_fallback = precursor.is_fallback or precursor.source_type == "eu_default"
    see_val = precursor.embedded_see_tco2_per_tonne
    if see_val is None or see_val <= 0:
        raise ValueError(
            f"Missing embedded SEE for precursor '{precursor.material_name}' (CN {precursor.cn_code})."
        )

    mass_tonnes = to_metric_tonnes(precursor.consumed_quantity, precursor.unit)
    precursor_tco2 = mass_tonnes * see_val
    return precursor_tco2, is_fallback, []


def calculate_product_see(
    request: DeterministicCalculationRequest,
    db: Optional[Session] = None,
) -> DeterministicCalculationResult:
    """
    Master deterministic calculation service.
    Follows official CBAM formula for specific embedded emissions:

    SEE = [Allocated Scope 1 + (delta_CN * Allocated Scope 2) + Precursor Emissions] / Net Target Production (tonnes)
    """
    resolved_request, fallback_notes = _resolve_request_factors(request, db)
    any_fallback_used = any(
        prec.is_fallback or prec.source_type == "eu_default" for prec in resolved_request.precursors
    )

    # 1. Net Target and Total Facility Production (tonnes)
    target_tonnes = to_metric_tonnes(
        resolved_request.production.target_production_quantity,
        resolved_request.production.target_production_unit,
    )
    total_facility_tonnes = to_metric_tonnes(
        resolved_request.production.total_facility_production_quantity,
        resolved_request.production.total_facility_production_unit,
    )

    # 2. Multi-Product Mass Allocation Factor (alpha_p)
    alpha_p = compute_mass_allocation_factor(target_tonnes, total_facility_tonnes)

    # 3. Delta CN Configuration (Scope 2 inclusion flag)
    delta_cn = determine_delta_cn(resolved_request.cn_code, db)

    # 4. Scope 1 Combustion & Process Emissions
    facility_gross_scope1 = 0.0
    allocated_scope1 = 0.0

    for fuel in resolved_request.fuels:
        gross_f, alloc_f, _ = calculate_fuel_emissions(
            fuel,
            alpha_p,
            apply_allocation=resolved_request.apply_allocation_to_shared_energy,
        )
        facility_gross_scope1 += gross_f
        allocated_scope1 += alloc_f

    # Process Emissions (if any)
    if resolved_request.process_emissions_tco2 > 0:
        facility_gross_scope1 += resolved_request.process_emissions_tco2
        allocated_scope1 += (
            resolved_request.process_emissions_tco2 * alpha_p
            if resolved_request.apply_allocation_to_shared_energy
            else resolved_request.process_emissions_tco2
        )

    # 5. Scope 2 Grid Electricity Emissions
    facility_gross_scope2 = 0.0
    allocated_scope2 = 0.0

    if resolved_request.electricity:
        gross_e, alloc_e, _ = calculate_electricity_emissions(
            resolved_request.electricity,
            alpha_p,
            apply_allocation=resolved_request.apply_allocation_to_shared_energy,
        )
        facility_gross_scope2 = gross_e
        allocated_scope2 = alloc_e

    # 6. Precursor Material Emissions
    total_precursor_emissions = 0.0
    for prec in resolved_request.precursors:
        prec_emissions, _, _ = calculate_precursor_emissions(prec)
        total_precursor_emissions += prec_emissions

    # 7. Total Embedded Emissions (tCO2)
    indirect_contribution = allocated_scope2 if delta_cn else 0.0
    total_embedded_emissions = allocated_scope1 + indirect_contribution + total_precursor_emissions

    # 8. Specific Embedded Emissions (SEE in tCO2 / tonne)
    see = total_embedded_emissions / target_tonnes

    # 9. Data Quality Rating
    if any_fallback_used:
        data_quality = DataQualityRating.FALLBACK_DEFAULT
    else:
        has_low_conf = any(f.confidence_score < 0.90 for f in resolved_request.fuels)
        if resolved_request.electricity and resolved_request.electricity.confidence_score < 0.90:
            has_low_conf = True
        if any(p.confidence_score < 0.90 for p in resolved_request.precursors):
            has_low_conf = True

        data_quality = DataQualityRating.HYBRID_ESTIMATED if has_low_conf else DataQualityRating.ACTUAL_PRIMARY

    # 10. LaTeX Formula representation for auditable reporting
    formula_latex = (
        r"\text{SEE} = \frac{\alpha_p \cdot \text{Dir} + \delta_{\text{CN}} \cdot \alpha_p \cdot \text{Ind} "
        r"+ \sum (M_{\text{prec}} \cdot \text{SEE}_{\text{prec}})}{\text{Production (t)}} = "
        rf"\frac{{{allocated_scope1:.4f} + ({1 if delta_cn else 0} \times {allocated_scope2:.4f}) + {total_precursor_emissions:.4f}}}{{{target_tonnes:.2f}}} = {see:.6f}"
        + r"\text{ tCO}_2/\text{t}"
    )

    # 11. Uncertainty Quantification (Monte Carlo simulation)
    uncertainty_result = None
    uncertainty_low = None
    uncertainty_high = None

    if resolved_request.run_monte_carlo:
        from app.modules.uncertainty.monte_carlo import run_monte_carlo_simulation
        uncertainty_result = run_monte_carlo_simulation(
            request=resolved_request,
            deterministic_see=see,
            alpha_p=alpha_p,
            delta_cn=delta_cn,
            target_tonnes=target_tonnes,
            iterations=resolved_request.monte_carlo_iterations,
        )
        uncertainty_low = uncertainty_result.p5
        uncertainty_high = uncertainty_result.p95

    # 12. Input Snapshot Freeze
    input_snapshot = {
        "reporting_period_id": resolved_request.reporting_period_id,
        "cn_code": resolved_request.cn_code,
        "delta_cn": delta_cn,
        "alpha_p": alpha_p,
        "target_production_tonnes": target_tonnes,
        "total_facility_production_tonnes": total_facility_tonnes,
        "fuel_factors": [
            {
                "fuel_name": fuel.fuel_name,
                "quantity": fuel.quantity,
                "unit": fuel.unit,
                "ncv_gj_per_unit": fuel.ncv,
                "ef_tco2_per_gj": fuel.ef,
                "oxidation_factor": fuel.oxidation_factor,
                "is_shared_utility": fuel.is_shared_utility,
            }
            for fuel in resolved_request.fuels
        ],
        "electricity_factor": (
            {
                "source_name": resolved_request.electricity.source_name,
                "consumed_quantity": resolved_request.electricity.consumed_quantity,
                "unit": resolved_request.electricity.unit,
                "grid_ef_tco2_per_mwh": resolved_request.electricity.grid_ef_tco2_per_mwh,
                "is_shared_utility": resolved_request.electricity.is_shared_utility,
            }
            if resolved_request.electricity
            else None
        ),
        "precursor_factors": [
            {
                "material_name": prec.material_name,
                "cn_code": prec.cn_code,
                "consumed_quantity": prec.consumed_quantity,
                "unit": prec.unit,
                "embedded_see_tco2_per_tonne": prec.embedded_see_tco2_per_tonne,
                "source_type": prec.source_type,
                "is_fallback": prec.is_fallback,
                "fallback_markup_pct": prec.fallback_markup_pct,
            }
            for prec in resolved_request.precursors
        ],
        "gross_scope1_tco2": facility_gross_scope1,
        "allocated_scope1_tco2": allocated_scope1,
        "gross_scope2_tco2": facility_gross_scope2,
        "allocated_scope2_tco2": allocated_scope2,
        "precursor_emissions_tco2": total_precursor_emissions,
        "total_embedded_emissions_tco2": total_embedded_emissions,
        "see_tco2_per_tonne": see,
        "data_quality_rating": data_quality.value,
        "fallback_notes": fallback_notes,
    }

    return DeterministicCalculationResult(
        reporting_period_id=resolved_request.reporting_period_id,
        target_cn_code=resolved_request.cn_code,
        target_product_family=resolved_request.production.target_product_family,
        allocation_factor_alpha=alpha_p,
        includes_indirect_delta_cn=delta_cn,
        data_quality_rating=data_quality,
        facility_gross_scope1_tco2=round(facility_gross_scope1, 6),
        allocated_scope1_direct_tco2=round(allocated_scope1, 6),
        facility_gross_scope2_tco2=round(facility_gross_scope2, 6),
        allocated_scope2_indirect_tco2=round(allocated_scope2, 6),
        precursor_emissions_tco2=round(total_precursor_emissions, 6),
        total_embedded_emissions_tco2=round(total_embedded_emissions, 6),
        net_target_production_tonnes=round(target_tonnes, 4),
        specific_embedded_emissions_see=round(see, 6),
        see_unit="tCO2/t",
        uncertainty=uncertainty_result,
        uncertainty_low_see=round(uncertainty_low, 6) if uncertainty_low is not None else None,
        uncertainty_high_see=round(uncertainty_high, 6) if uncertainty_high is not None else None,
        confidence_interval_pct=95.0,
        formula_latex=formula_latex,
        fallback_notes=fallback_notes,
        input_snapshot=input_snapshot,
    )
