"""Monte Carlo Uncertainty Quantification Engine for CBAM Embedded Emissions.

Computes statistical confidence bands (P5, P50, P95) across multi-distribution
sampling of OCR-extracted values, physical meters, and regulatory fallback factors.
"""

from typing import Optional
import numpy as np
from app.modules.calculation.unit_converter import (
    to_energy_gigajoules,
    to_megawatt_hours,
    to_metric_tonnes,
)
from app.schemas.calculation import (
    DeterministicCalculationRequest,
    UncertaintyDistributionResult,
)


def sample_truncated_normal(
    mean: float,
    confidence: float,
    size: int,
    relative_scale: float = 1.0,
) -> np.ndarray:
    """
    Samples from a Truncated Normal distribution bounded strictly at > 0.
    Standard deviation sigma is proportional to (1 - confidence score).
    """
    if mean <= 0:
        return np.zeros(size)

    # Higher confidence score yields smaller standard deviation
    uncertainty_fraction = max(0.01, 1.0 - confidence) * relative_scale
    sigma = (mean * uncertainty_fraction) / 1.96  # 95% within +/- uncertainty

    samples = np.random.normal(loc=mean, scale=sigma, size=size)
    # Truncate at a safe minimum (10% of mean) to avoid non-physical negative numbers
    return np.maximum(samples, mean * 0.1)


def sample_triangular_fallback(mode: float, size: int, spread: float = 0.20) -> np.ndarray:
    """
    Samples from a Triangular distribution (mode, min = mode * (1-spread), max = mode * (1+spread)).
    Used for official regulatory default fallbacks (typically +/- 20% uncertainty).
    """
    if mode <= 0:
        return np.zeros(size)

    left = mode * (1.0 - spread)
    right = mode * (1.0 + spread)
    return np.random.triangular(left=left, mode=mode, right=right, size=size)


def sample_lognormal_meter(mean: float, size: int, cv: float = 0.02) -> np.ndarray:
    """
    Samples from a Log-Normal distribution representing physical utility-grade revenue meters
    (e.g., Class 0.2 or Class 0.5 CT/PT meters with coefficient of variation cv ~ 2%).
    """
    if mean <= 0:
        return np.zeros(size)

    sigma = np.sqrt(np.log(1.0 + cv**2))
    mu = np.log(mean) - 0.5 * sigma**2
    return np.random.lognormal(mean=mu, sigma=sigma, size=size)


def run_monte_carlo_simulation(
    request: DeterministicCalculationRequest,
    deterministic_see: float,
    alpha_p: float,
    delta_cn: bool,
    target_tonnes: float,
    iterations: int = 5000,
    random_seed: Optional[int] = 42,
) -> UncertaintyDistributionResult:
    """
    Runs vectorized Monte Carlo simulation (default 5,000 iterations)
    evaluating empirical percentiles (P5, P50, P95) for specific embedded emissions.
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # 1. Sample Net Target Production Quantity (tonnes)
    sim_target_tonnes = sample_truncated_normal(
        mean=target_tonnes,
        confidence=0.98,  # Billing/weighbridge logs have high baseline certainty
        size=iterations,
    )

    # 2. Sample Scope 1 Fuel Emissions (tCO2)
    sim_allocated_scope1 = np.zeros(iterations)

    for fuel in request.fuels:
        # Determine sampling strategy
        if fuel.confidence_score >= 0.95:
            # High-confidence metered delivery -> Log-normal
            sim_q = sample_lognormal_meter(fuel.quantity, iterations, cv=0.03)
        else:
            # OCR extracted invoice -> Truncated normal
            sim_q = sample_truncated_normal(fuel.quantity, fuel.confidence_score, iterations)

        ncv = fuel.ncv or 0.0402
        ef = fuel.ef or 0.0774
        of = fuel.oxidation_factor if fuel.oxidation_factor is not None else 1.0

        # Fuel quantity to GJ
        sim_energy_gj = sim_q * ncv
        sim_emissions = sim_energy_gj * ef * of

        if request.apply_allocation_to_shared_energy and fuel.is_shared_utility:
            sim_allocated_scope1 += sim_emissions * alpha_p
        else:
            sim_allocated_scope1 += sim_emissions

    # Process emissions (if any)
    if request.process_emissions_tco2 > 0:
        sim_allocated_scope1 += request.process_emissions_tco2 * (
            alpha_p if request.apply_allocation_to_shared_energy else 1.0
        )

    # 3. Sample Scope 2 Electricity Emissions (tCO2)
    sim_allocated_scope2 = np.zeros(iterations)

    if request.electricity and request.electricity.consumed_quantity > 0:
        elec = request.electricity
        mwh = to_megawatt_hours(elec.consumed_quantity, elec.unit)

        # Utility grid meters have revenue-grade logging -> Log-normal distribution
        if elec.confidence_score >= 0.95:
            sim_mwh = sample_lognormal_meter(mwh, iterations, cv=0.02)
        else:
            sim_mwh = sample_truncated_normal(mwh, elec.confidence_score, iterations)

        grid_ef = elec.grid_ef_tco2_per_mwh or 0.716
        # Grid factor carries slight regional variance (+/- 5% triangular)
        sim_grid_ef = sample_triangular_fallback(grid_ef, iterations, spread=0.05)

        sim_emissions_scope2 = sim_mwh * sim_grid_ef

        if request.apply_allocation_to_shared_energy and elec.is_shared_utility:
            sim_allocated_scope2 += sim_emissions_scope2 * alpha_p
        else:
            sim_allocated_scope2 += sim_emissions_scope2

    # 4. Sample Precursor Emissions (tCO2)
    sim_precursor_emissions = np.zeros(iterations)

    for prec in request.precursors:
        mass = to_metric_tonnes(prec.consumed_quantity, prec.unit)
        sim_mass = sample_truncated_normal(mass, prec.confidence_score, iterations)

        is_fallback = prec.is_fallback or prec.source_type == "eu_default"
        see_val = prec.embedded_see_tco2_per_tonne

        if is_fallback or see_val is None or see_val <= 0:
            # Fallback default factor -> Triangular distribution with +/- 20% policy bounds
            base_default = see_val or 2.24
            sim_see = sample_triangular_fallback(base_default, iterations, spread=0.20)
            markup_multiplier = 1.0 + ((prec.fallback_markup_pct or 10.0) / 100.0)
            sim_see = sim_see * markup_multiplier
        else:
            # Supplier actual value with test certificate -> Truncated normal
            sim_see = sample_truncated_normal(see_val, prec.confidence_score, iterations)

        sim_precursor_emissions += sim_mass * sim_see

    # 5. Compute Simulated Total and SEE distributions
    indirect_term = sim_allocated_scope2 if delta_cn else np.zeros(iterations)
    sim_total_embedded = sim_allocated_scope1 + indirect_term + sim_precursor_emissions
    sim_see_array = sim_total_embedded / sim_target_tonnes

    # 6. Statistical Summaries (P5, P50, P95)
    p5 = float(np.percentile(sim_see_array, 5))
    p50 = float(np.percentile(sim_see_array, 50))
    p95 = float(np.percentile(sim_see_array, 95))
    mean_val = float(np.mean(sim_see_array))
    std_val = float(np.std(sim_see_array))

    return UncertaintyDistributionResult(
        p5=round(p5, 6),
        p50=round(p50, 6),
        p95=round(p95, 6),
        mean=round(mean_val, 6),
        std_dev=round(std_val, 6),
        iterations=iterations,
    )
