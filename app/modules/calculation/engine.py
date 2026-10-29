"""Deterministic CBAM Specific Embedded Emissions (SEE) Calculation Engine.

STRICT PRINCIPLE: AI NEVER PERFORMS EMISSIONS ARITHMETIC.
All calculations are 100% deterministic, testable, and auditable.
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.modules.calculation.unit_converter import (
    to_energy_gigajoules,
    to_megawatt_hours,
    to_metric_tonnes,
)
from app.schemas.calculation import (
    DataQualityRating,
    DeterministicCalculationRequest,
    DeterministicCalculationResult,
    FuelCombustionItem,
    PrecursorMaterialItem,
)

# EU CBAM Commission Implementing Regulation default fallbacks (tCO2/t or default values)
OFFICIAL_CBAM_FALLBACKS: Dict[str, Dict[str, float]] = {
    # Steel Precursor: Alloy Steel Wire Rod (India)
    "7228 30": {
        "default_see_tco2_per_tonne": 2.24,
        "default_markup_pct": 10.0,  # 10% penalty markup for unverified fallback data
        "description": "EU CBAM Default - Alloy Steel Wire Rod (India)",
    },
    # Non-alloy wire rod (India)
    "7213 10": {
        "default_see_tco2_per_tonne": 2.15,
        "default_markup_pct": 10.0,
        "description": "EU CBAM Default - Bars and rods, hot-rolled (India)",
    },
    # Crude Steel
    "7207": {
        "default_see_tco2_per_tonne": 1.95,
        "default_markup_pct": 10.0,
        "description": "EU CBAM Default - Semi-finished products of iron or non-alloy steel",
    },
}

# Standard Default Grid Emission Factors (tCO2 / MWh)
OFFICIAL_GRID_FACTORS: Dict[str, float] = {
    "IN": 0.716,  # CEA CO2 Baseline Database v19
    "EU_DEFAULT_IN": 0.820,  # EU CBAM default for Indian electricity
    "GLOBAL": 0.700,
}

# Standard Fuel Defaults (NCV in GJ/unit, EF in tCO2/GJ)
OFFICIAL_FUEL_FACTORS: Dict[str, Dict[str, float]] = {
    "furnace oil": {"ncv": 0.0402, "ef": 0.0774, "unit": "litre"},
    "diesel": {"ncv": 0.0357, "ef": 0.0741, "unit": "litre"},
    "natural gas": {"ncv": 0.0385, "ef": 0.0561, "unit": "nm3"},
    "lpg": {"ncv": 0.0461, "ef": 0.0631, "unit": "kg"},
}


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


def determine_delta_cn(cn_code: str, db: Optional[Session] = None) -> bool:
    """
    Determines whether the 8-digit CN code requires Scope 2 indirect emissions (delta_CN = 1).
    For Iron & Steel Fasteners (CN 7318 group), delta_CN = True under definitive rules.
    """
    clean_code = cn_code.replace(" ", "")

    # Query DB if available
    if db is not None:
        from app.db.models import CNCodeRegistry
        entry = db.query(CNCodeRegistry).filter_by(cn_code=cn_code).first()
        if not entry:
            entry = db.query(CNCodeRegistry).filter(CNCodeRegistry.cn_code.like(f"%{clean_code[:4]}%")).first()
        if entry:
            return bool(entry.includes_indirect_emissions)

    # Steel Fasteners (CN 7318) and related steel products include indirect emissions (delta_CN = 1)
    if clean_code.startswith("7318") or clean_code.startswith("72"):
        return True

    return True


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
    notes = []
    fuel_key = fuel.fuel_name.lower().strip()

    # Resolve NCV
    ncv = fuel.ncv
    if ncv is None or ncv <= 0:
        matched_default = None
        for k, v in OFFICIAL_FUEL_FACTORS.items():
            if k in fuel_key:
                matched_default = v
                break
        if matched_default:
            ncv = matched_default["ncv"]
            notes.append(f"Used default NCV for {fuel.fuel_name}: {ncv} GJ/{fuel.unit}")
        else:
            raise ValueError(f"Missing Net Calorific Value (NCV) for fuel '{fuel.fuel_name}'.")

    # Resolve EF
    ef = fuel.ef
    if ef is None or ef <= 0:
        matched_default = None
        for k, v in OFFICIAL_FUEL_FACTORS.items():
            if k in fuel_key:
                matched_default = v
                break
        if matched_default:
            ef = matched_default["ef"]
            notes.append(f"Used default Emission Factor for {fuel.fuel_name}: {ef} tCO2/GJ")
        else:
            raise ValueError(f"Missing Emission Factor (EF) for fuel '{fuel.fuel_name}'.")

    of = fuel.oxidation_factor if fuel.oxidation_factor is not None else 1.0

    # Convert quantity to GJ
    energy_gj = to_energy_gigajoules(fuel.quantity, fuel.unit, ncv)
    gross_tco2 = energy_gj * ef * of

    # Allocation: if fuel is shared facility utility, multiply by alpha_p
    if apply_allocation and fuel.is_shared_utility:
        allocated_tco2 = gross_tco2 * allocation_factor_alpha
    else:
        allocated_tco2 = gross_tco2

    return gross_tco2, allocated_tco2, notes


def calculate_electricity_emissions(
    electricity_item,
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

    notes = []
    # Convert consumed quantity to MWh
    mwh = to_megawatt_hours(electricity_item.consumed_quantity, electricity_item.unit)

    # Resolve grid emission factor
    grid_ef = electricity_item.grid_ef_tco2_per_mwh
    if grid_ef is None or grid_ef <= 0:
        grid_ef = OFFICIAL_GRID_FACTORS["IN"]  # Default CEA baseline
        notes.append(f"Used default CEA v19 grid emission factor: {grid_ef} tCO2/MWh")

    gross_tco2 = mwh * grid_ef

    if apply_allocation and electricity_item.is_shared_utility:
        allocated_tco2 = gross_tco2 * allocation_factor_alpha
    else:
        allocated_tco2 = gross_tco2

    return gross_tco2, allocated_tco2, notes


def calculate_precursor_emissions(
    precursor: PrecursorMaterialItem,
) -> Tuple[float, bool, List[str]]:
    """
    Calculates embedded emissions from a precursor material.
    Emissions = Mass (tonnes) * Embedded SEE (tCO2/tonne)
    If unverified / fallback, applies mandatory penalty markup.
    Returns: (precursor_tco2, is_fallback_used, notes)
    """
    notes = []
    is_fallback = precursor.is_fallback or precursor.source_type == "eu_default"

    # Convert consumed quantity to metric tonnes
    mass_tonnes = to_metric_tonnes(precursor.consumed_quantity, precursor.unit)

    see_val = precursor.embedded_see_tco2_per_tonne

    # Check if fallback is required
    if see_val is None or see_val <= 0 or is_fallback:
        is_fallback = True
        cn_key = precursor.cn_code or "7228 30"
        fallback_info = OFFICIAL_CBAM_FALLBACKS.get(cn_key, OFFICIAL_CBAM_FALLBACKS["7228 30"])
        base_fallback_see = fallback_info["default_see_tco2_per_tonne"]
        markup_pct = precursor.fallback_markup_pct or fallback_info["default_markup_pct"]

        # Apply mandatory markup penalty
        see_val = base_fallback_see * (1.0 + (markup_pct / 100.0))
        notes.append(
            f"Precursor '{precursor.material_name}' (CN {cn_key}): Applied EU default fallback SEE of "
            f"{base_fallback_see} tCO2/t with +{markup_pct}% penalty markup -> {see_val:.4f} tCO2/t."
        )

    precursor_tco2 = mass_tonnes * see_val
    return precursor_tco2, is_fallback, notes


def calculate_product_see(
    request: DeterministicCalculationRequest,
    db: Optional[Session] = None,
) -> DeterministicCalculationResult:
    """
    Master deterministic calculation service.
    Follows official CBAM formula for specific embedded emissions:

    SEE = [Allocated Scope 1 + (delta_CN * Allocated Scope 2) + Precursor Emissions] / Net Target Production (tonnes)
    """
    fallback_notes: List[str] = []
    any_fallback_used = False

    # 1. Net Target and Total Facility Production (tonnes)
    target_tonnes = to_metric_tonnes(
        request.production.target_production_quantity,
        request.production.target_production_unit,
    )
    total_facility_tonnes = to_metric_tonnes(
        request.production.total_facility_production_quantity,
        request.production.total_facility_production_unit,
    )

    # 2. Multi-Product Mass Allocation Factor (alpha_p)
    alpha_p = compute_mass_allocation_factor(target_tonnes, total_facility_tonnes)

    # 3. Delta CN Configuration (Scope 2 inclusion flag)
    delta_cn = determine_delta_cn(request.cn_code, db)

    # 4. Scope 1 Combustion & Process Emissions
    facility_gross_scope1 = 0.0
    allocated_scope1 = 0.0

    for fuel in request.fuels:
        gross_f, alloc_f, f_notes = calculate_fuel_emissions(
            fuel,
            alpha_p,
            apply_allocation=request.apply_allocation_to_shared_energy,
        )
        facility_gross_scope1 += gross_f
        allocated_scope1 += alloc_f
        fallback_notes.extend(f_notes)

    # Process Emissions (if any)
    if request.process_emissions_tco2 > 0:
        facility_gross_scope1 += request.process_emissions_tco2
        allocated_scope1 += (
            request.process_emissions_tco2 * alpha_p
            if request.apply_allocation_to_shared_energy
            else request.process_emissions_tco2
        )

    # 5. Scope 2 Grid Electricity Emissions
    facility_gross_scope2 = 0.0
    allocated_scope2 = 0.0

    if request.electricity:
        gross_e, alloc_e, e_notes = calculate_electricity_emissions(
            request.electricity,
            alpha_p,
            apply_allocation=request.apply_allocation_to_shared_energy,
        )
        facility_gross_scope2 = gross_e
        allocated_scope2 = alloc_e
        fallback_notes.extend(e_notes)

    # 6. Precursor Material Emissions
    total_precursor_emissions = 0.0
    for prec in request.precursors:
        prec_emissions, is_fb, prec_notes = calculate_precursor_emissions(prec)
        total_precursor_emissions += prec_emissions
        if is_fb:
            any_fallback_used = True
        fallback_notes.extend(prec_notes)

    # 7. Total Embedded Emissions (tCO2)
    indirect_contribution = allocated_scope2 if delta_cn else 0.0
    total_embedded_emissions = allocated_scope1 + indirect_contribution + total_precursor_emissions

    # 8. Specific Embedded Emissions (SEE in tCO2 / tonne)
    see = total_embedded_emissions / target_tonnes

    # 9. Data Quality Rating
    if any_fallback_used:
        data_quality = DataQualityRating.FALLBACK_DEFAULT
    else:
        has_low_conf = any(f.confidence_score < 0.90 for f in request.fuels)
        if request.electricity and request.electricity.confidence_score < 0.90:
            has_low_conf = True
        if any(p.confidence_score < 0.90 for p in request.precursors):
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

    if request.run_monte_carlo:
        from app.modules.uncertainty.monte_carlo import run_monte_carlo_simulation
        uncertainty_result = run_monte_carlo_simulation(
            request=request,
            deterministic_see=see,
            alpha_p=alpha_p,
            delta_cn=delta_cn,
            target_tonnes=target_tonnes,
            iterations=request.monte_carlo_iterations,
        )
        uncertainty_low = uncertainty_result.p5
        uncertainty_high = uncertainty_result.p95

    # 12. Input Snapshot Freeze
    input_snapshot = {
        "reporting_period_id": request.reporting_period_id,
        "cn_code": request.cn_code,
        "delta_cn": delta_cn,
        "alpha_p": alpha_p,
        "target_production_tonnes": target_tonnes,
        "total_facility_production_tonnes": total_facility_tonnes,
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
        reporting_period_id=request.reporting_period_id,
        target_cn_code=request.cn_code,
        target_product_family=request.production.target_product_family,
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
