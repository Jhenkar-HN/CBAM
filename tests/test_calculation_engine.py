"""Unit test suite verifying deterministic calculations, unit conversions, and Monte Carlo uncertainty."""

import pytest
from app.modules.calculation.unit_converter import (
    to_energy_gigajoules,
    to_megawatt_hours,
    to_metric_tonnes,
)
from app.modules.calculation.engine import (
    calculate_product_see,
    compute_mass_allocation_factor,
    determine_delta_cn,
)
from app.modules.uncertainty.monte_carlo import run_monte_carlo_simulation
from app.schemas.calculation import (
    DataQualityRating,
    DeterministicCalculationRequest,
    ElectricityConsumptionItem,
    FuelCombustionItem,
    PrecursorMaterialItem,
    ProductionAllocationInput,
)


# =====================================================================
# 1. Physical Unit Converter Tests
# =====================================================================

def test_unit_converter_mass():
    assert to_metric_tonnes(1.0, "tonne") == 1.0
    assert to_metric_tonnes(1000.0, "kg") == 1.0
    assert to_metric_tonnes(500.0, "MT") == 500.0
    assert pytest.approx(to_metric_tonnes(2204.62, "lbs"), rel=1e-3) == 1.0

    with pytest.raises(ValueError, match="Unsupported mass unit"):
        to_metric_tonnes(100.0, "unknown_unit")

    with pytest.raises(ValueError, match="cannot be negative"):
        to_metric_tonnes(-5.0, "kg")


def test_unit_converter_electricity():
    assert to_megawatt_hours(1.0, "MWh") == 1.0
    assert to_megawatt_hours(1000.0, "kWh") == 1.0
    assert to_megawatt_hours(250000.0, "units") == 250.0
    assert to_megawatt_hours(1.5, "GWh") == 1500.0

    with pytest.raises(ValueError, match="Unsupported electricity unit"):
        to_megawatt_hours(100.0, "volts")


def test_unit_converter_energy_gj():
    # Direct energy conversions
    assert to_energy_gigajoules(1.0, "GJ") == 1.0
    assert to_energy_gigajoules(1000.0, "MJ") == 1.0
    assert to_energy_gigajoules(1.0, "TJ") == 1000.0

    # Physical fuel conversions via NCV
    # 15,000 litres of furnace oil with NCV = 0.0402 GJ/l -> 603.0 GJ
    gj = to_energy_gigajoules(15000.0, "litre", ncv_gj_per_unit=0.0402)
    assert pytest.approx(gj, rel=1e-5) == 603.0

    with pytest.raises(ValueError, match="Net Calorific Value .* required"):
        to_energy_gigajoules(100.0, "litre", ncv_gj_per_unit=None)


# =====================================================================
# 2. Mass Allocation Factor & Delta CN Tests
# =====================================================================

def test_mass_allocation_factor():
    # 500 t target / 625 t total = 0.8
    alpha = compute_mass_allocation_factor(500.0, 625.0)
    assert alpha == 0.8

    # 100% allocation if facility produces exclusively target goods
    assert compute_mass_allocation_factor(500.0, 500.0) == 1.0

    # Error if target exceeds total facility
    with pytest.raises(ValueError, match="cannot exceed total facility"):
        compute_mass_allocation_factor(700.0, 500.0)

    # Error if zero or negative
    with pytest.raises(ValueError, match="greater than 0"):
        compute_mass_allocation_factor(0.0, 500.0)


def test_determine_delta_cn():
    # Steel fasteners (CN 7318 group) require indirect emissions
    assert determine_delta_cn("7318 15 82") is True
    assert determine_delta_cn("7318 16 00") is True
    assert determine_delta_cn("7228 30") is True


# =====================================================================
# 3. Deterministic Benchmark Scenario: Steel Fastener Manufacturing
# =====================================================================

def test_deterministic_calculation_benchmark():
    """
    Known Benchmark Scenario for Indian Steel Fastener Exporter:
    - Target: 500 tonnes of Steel Fasteners (CN 7318 15 82)
    - Total Facility Production: 625 tonnes (alpha_p = 0.80)
    - Scope 1 Fuel: 15,000 litres Furnace Oil (NCV = 0.0402 GJ/l, EF = 0.0774 tCO2/GJ, OF = 1.0)
        Gross = 15000 * 0.0402 * 0.0774 = 46.6722 tCO2
        Allocated (alpha_p = 0.80) = 37.33776 tCO2
    - Scope 2 Electricity: 250,000 kWh = 250 MWh (Grid EF = 0.716 tCO2/MWh)
        Gross = 250 * 0.716 = 179.0 tCO2
        Allocated (alpha_p = 0.80) = 143.20 tCO2
    - Scope 2 Flag: delta_CN = 1 (included)
    - Precursor: 520 tonnes Steel Wire Rod (actual SEE = 1.85 tCO2/t)
        Precursor Emissions = 520 * 1.85 = 962.0 tCO2
    - Total Embedded Emissions = 37.33776 + 143.20 + 962.0 = 1142.53776 tCO2
    - Net Production = 500.0 tonnes
    - SEE = 1142.53776 / 500.0 = 2.28507552 tCO2/t
    """
    request = DeterministicCalculationRequest(
        reporting_period_id=101,
        cn_code="7318 15 82",
        production=ProductionAllocationInput(
            target_product_family="Steel Fasteners (CN 7318 15 82)",
            target_production_quantity=500.0,
            target_production_unit="tonne",
            total_facility_production_quantity=625.0,
            total_facility_production_unit="tonne",
        ),
        fuels=[
            FuelCombustionItem(
                fuel_name="Furnace Oil",
                quantity=15000.0,
                unit="litre",
                ncv=0.0402,
                ef=0.0774,
                oxidation_factor=1.0,
                confidence_score=0.96,
                is_shared_utility=True,
            )
        ],
        process_emissions_tco2=0.0,
        electricity=ElectricityConsumptionItem(
            source_name="DHBVN Industrial Grid",
            consumed_quantity=250000.0,
            unit="kWh",
            grid_ef_tco2_per_mwh=0.716,
            confidence_score=0.97,
            is_shared_utility=True,
        ),
        precursors=[
            PrecursorMaterialItem(
                material_name="Steel Wire Rod (DRI-EAF Route)",
                consumed_quantity=520.0,
                unit="tonne",
                embedded_see_tco2_per_tonne=1.85,
                source_type="supplier_actual",
                confidence_score=0.95,
                is_fallback=False,
            )
        ],
        apply_allocation_to_shared_energy=True,
        run_monte_carlo=True,
        monte_carlo_iterations=2000,
    )

    result = calculate_product_see(request)

    # 1. Assert Allocation and CN flags
    assert result.allocation_factor_alpha == 0.8
    assert result.includes_indirect_delta_cn is True

    # 2. Assert Exact Deterministic Subtotals
    assert pytest.approx(result.facility_gross_scope1_tco2, rel=1e-5) == 46.6722
    assert pytest.approx(result.allocated_scope1_direct_tco2, rel=1e-5) == 37.33776

    assert pytest.approx(result.facility_gross_scope2_tco2, rel=1e-5) == 179.0
    assert pytest.approx(result.allocated_scope2_indirect_tco2, rel=1e-5) == 143.20

    assert pytest.approx(result.precursor_emissions_tco2, rel=1e-5) == 962.0
    assert pytest.approx(result.total_embedded_emissions_tco2, rel=1e-5) == 1142.53776

    # 3. Assert Exact Final Metric (SEE)
    expected_see = 1142.53776 / 500.0  # 2.28507552 tCO2/t
    assert pytest.approx(result.specific_embedded_emissions_see, rel=1e-5) == expected_see

    # 4. Assert Data Quality
    assert result.data_quality_rating == DataQualityRating.ACTUAL_PRIMARY

    # 5. Assert Monte Carlo Uncertainty Range
    assert result.uncertainty is not None
    assert result.uncertainty_low_see <= result.uncertainty.p50 <= result.uncertainty_high_see
    # Simulated median should be within 3% of deterministic value
    assert pytest.approx(result.uncertainty.p50, rel=0.03) == expected_see


# =====================================================================
# 4. Precursor Fallback & Penalty Markup Test
# =====================================================================

def test_precursor_fallback_and_markup():
    """
    Verifies that when a precursor has no verified actual SEE, the engine:
    1. Uses the official fallback factor (2.24 tCO2/t for alloy wire rod).
    2. Applies the mandatory +10% penalty markup -> 2.464 tCO2/t.
    3. Sets data_quality_rating to FALLBACK_DEFAULT.
    """
    request = DeterministicCalculationRequest(
        reporting_period_id=102,
        cn_code="7318 15 82",
        production=ProductionAllocationInput(
            target_product_family="Steel Fasteners",
            target_production_quantity=100.0,
            target_production_unit="tonne",
            total_facility_production_quantity=100.0,
            total_facility_production_unit="tonne",
        ),
        precursors=[
            PrecursorMaterialItem(
                material_name="Wire Rod Unverified",
                consumed_quantity=105.0,
                unit="tonne",
                embedded_see_tco2_per_tonne=None,  # Missing actual
                source_type="eu_default",
                cn_code="7228 30",
                is_fallback=True,
                fallback_markup_pct=10.0,
            )
        ],
        apply_allocation_to_shared_energy=True,
        run_monte_carlo=False,
    )

    result = calculate_product_see(request)

    # 2.24 * 1.10 = 2.464 tCO2/t
    # 105 tonnes * 2.464 = 258.72 tCO2
    assert pytest.approx(result.precursor_emissions_tco2, rel=1e-4) == 258.72
    assert result.data_quality_rating == DataQualityRating.FALLBACK_DEFAULT
    assert any("penalty markup" in note for note in result.fallback_notes)


# =====================================================================
# 5. Indirect Emissions Toggle Test (delta_CN = 0)
# =====================================================================

def test_delta_cn_zero_excludes_indirect():
    """Verifies that if delta_CN is False, Scope 2 emissions are excluded from SEE numerator."""
    request = DeterministicCalculationRequest(
        reporting_period_id=103,
        cn_code="CUSTOM_NO_INDIRECT",  # Custom code simulating delta_cn = 0
        production=ProductionAllocationInput(
            target_product_family="Direct Only Goods",
            target_production_quantity=100.0,
            target_production_unit="tonne",
            total_facility_production_quantity=100.0,
            total_facility_production_unit="tonne",
        ),
        fuels=[
            FuelCombustionItem(
                fuel_name="Diesel",
                quantity=1000.0,
                unit="litre",
                ncv=0.0357,
                ef=0.0741,
                oxidation_factor=1.0,
            )
        ],
        electricity=ElectricityConsumptionItem(
            source_name="Grid",
            consumed_quantity=10000.0,  # 10 MWh
            unit="kWh",
            grid_ef_tco2_per_mwh=0.716,  # 7.16 tCO2
        ),
        run_monte_carlo=False,
    )

    # Force delta_cn check
    from unittest.mock import patch
    with patch("app.modules.calculation.engine.determine_delta_cn", return_value=False):
        result = calculate_product_see(request)

    assert result.includes_indirect_delta_cn is False
    # Scope 2 calculated in background...
    assert pytest.approx(result.facility_gross_scope2_tco2, rel=1e-4) == 7.16
    # But total embedded must EXCLUDE Scope 2 when delta_CN is False!
    # Diesel = 1000 * 0.0357 * 0.0741 = 2.64537 tCO2
    assert pytest.approx(result.total_embedded_emissions_tco2, rel=1e-4) == 2.64537
    assert pytest.approx(result.specific_embedded_emissions_see, rel=1e-4) == (2.64537 / 100.0)


# =====================================================================
# 6. Monte Carlo Statistical Properties Test
# =====================================================================

def test_monte_carlo_statistical_properties():
    """Verifies that the Monte Carlo engine produces valid statistical ordering: P5 <= P50 <= P95."""
    request = DeterministicCalculationRequest(
        reporting_period_id=104,
        cn_code="7318 15 82",
        production=ProductionAllocationInput(
            target_product_family="Steel Screws",
            target_production_quantity=200.0,
            target_production_unit="tonne",
            total_facility_production_quantity=200.0,
            total_facility_production_unit="tonne",
        ),
        fuels=[
            FuelCombustionItem(
                fuel_name="Furnace Oil",
                quantity=5000.0,
                unit="litre",
                ncv=0.0402,
                ef=0.0774,
                confidence_score=0.90,
            )
        ],
        run_monte_carlo=True,
        monte_carlo_iterations=3000,
    )

    result = calculate_product_see(request)
    unc = result.uncertainty
    assert unc is not None
    assert unc.p5 < unc.p50 < unc.p95
    assert unc.std_dev > 0
    assert unc.iterations == 3000
