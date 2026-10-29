from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DataQualityRating(str, Enum):
    ACTUAL_PRIMARY = "ACTUAL_PRIMARY"
    HYBRID_ESTIMATED = "HYBRID_ESTIMATED"
    FALLBACK_DEFAULT = "FALLBACK_DEFAULT"


class FuelCombustionItem(BaseModel):
    fuel_name: str = Field(..., json_schema_extra={"example": "Furnace Oil"})
    quantity: float = Field(..., gt=0, json_schema_extra={"example": 15000.0})
    unit: str = Field(..., json_schema_extra={"example": "litre"})
    ncv: Optional[float] = Field(None, gt=0, description="Net Calorific Value in GJ per physical unit", json_schema_extra={"example": 0.0402})
    ncv_unit: Optional[str] = Field(default="GJ/unit", json_schema_extra={"example": "GJ/litre"})
    ef: Optional[float] = Field(None, gt=0, description="Emission factor in tCO2 per GJ", json_schema_extra={"example": 0.0774})
    ef_unit: Optional[str] = Field(default="tCO2/GJ", json_schema_extra={"example": "tCO2/GJ"})
    oxidation_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.95, ge=0.1, le=1.0)
    is_shared_utility: bool = Field(default=True, description="Whether this fuel is consumed across shared facility utilities")


class ElectricityConsumptionItem(BaseModel):
    source_name: str = Field(default="State Grid / PPA", json_schema_extra={"example": "DHBVN Industrial Grid"})
    consumed_quantity: float = Field(..., ge=0, json_schema_extra={"example": 250000.0})
    unit: str = Field(default="kWh", json_schema_extra={"example": "kWh"})
    grid_ef_tco2_per_mwh: Optional[float] = Field(None, gt=0, description="Grid emission factor in tCO2/MWh", json_schema_extra={"example": 0.716})
    confidence_score: float = Field(default=0.95, ge=0.1, le=1.0)
    is_shared_utility: bool = Field(default=True, description="Whether electricity is consumed across shared facility")


class PrecursorMaterialItem(BaseModel):
    material_name: str = Field(..., json_schema_extra={"example": "Steel Wire Rod (Crude Steel)"})
    consumed_quantity: float = Field(..., gt=0, json_schema_extra={"example": 520.0})
    unit: str = Field(default="tonne", json_schema_extra={"example": "tonne"})
    embedded_see_tco2_per_tonne: Optional[float] = Field(None, ge=0, description="Specific Embedded Emissions of precursor (tCO2/t)", json_schema_extra={"example": 1.85})
    source_type: str = Field(default="supplier_actual", json_schema_extra={"example": "supplier_actual or eu_default"})
    cn_code: Optional[str] = Field(default="7228 30", json_schema_extra={"example": "7228 30"})
    country_of_origin: str = Field(default="IN", json_schema_extra={"example": "IN"})
    confidence_score: float = Field(default=0.90, ge=0.1, le=1.0)
    is_fallback: bool = Field(default=False, description="Flag indicating if official fallback default was applied")
    fallback_markup_pct: float = Field(default=0.0, description="Mandatory EU default penalty markup percentage e.g. 10.0 for 10%")


class ProductionAllocationInput(BaseModel):
    target_product_family: str = Field(..., json_schema_extra={"example": "Steel Fasteners (CN 7318 15 82)"})
    target_production_quantity: float = Field(..., gt=0, description="Net production volume of target goods", json_schema_extra={"example": 500.0})
    target_production_unit: str = Field(default="tonne", json_schema_extra={"example": "tonne"})
    total_facility_production_quantity: float = Field(..., gt=0, description="Total plant production across all lines", json_schema_extra={"example": 625.0})
    total_facility_production_unit: str = Field(default="tonne", json_schema_extra={"example": "tonne"})
    scrap_quantity: float = Field(default=0.0, ge=0)
    scrap_unit: str = Field(default="tonne")


class UncertaintyDistributionResult(BaseModel):
    p5: float = Field(..., description="5th percentile (low bound)")
    p50: float = Field(..., description="50th percentile (median)")
    p95: float = Field(..., description="95th percentile (high bound)")
    mean: float = Field(..., description="Mean simulated SEE")
    std_dev: float = Field(..., description="Standard deviation")
    iterations: int = Field(default=5000)


class DeterministicCalculationRequest(BaseModel):
    reporting_period_id: int
    cn_code: str = Field(..., json_schema_extra={"example": "7318 15 82"})
    production: ProductionAllocationInput
    fuels: List[FuelCombustionItem] = Field(default_factory=list)
    process_emissions_tco2: float = Field(default=0.0, ge=0)
    electricity: Optional[ElectricityConsumptionItem] = None
    precursors: List[PrecursorMaterialItem] = Field(default_factory=list)
    apply_allocation_to_shared_energy: bool = Field(default=True, description="Apply alpha_p to unmetered shared Scope 1 and Scope 2")
    run_monte_carlo: bool = Field(default=True, description="Run Monte Carlo simulation for uncertainty quantification")
    monte_carlo_iterations: int = Field(default=5000, ge=500, le=50000)


class DeterministicCalculationResult(BaseModel):
    reporting_period_id: int
    target_cn_code: str
    target_product_family: str
    allocation_factor_alpha: float
    includes_indirect_delta_cn: bool
    data_quality_rating: DataQualityRating

    # Subtotals (tCO2)
    facility_gross_scope1_tco2: float
    allocated_scope1_direct_tco2: float

    facility_gross_scope2_tco2: float
    allocated_scope2_indirect_tco2: float

    precursor_emissions_tco2: float
    total_embedded_emissions_tco2: float

    # Final Metric
    net_target_production_tonnes: float
    specific_embedded_emissions_see: float  # tCO2 per tonne
    see_unit: str = "tCO2/t"

    # Uncertainty Quantification (Monte Carlo)
    uncertainty: Optional[UncertaintyDistributionResult] = None
    uncertainty_low_see: Optional[float] = None
    uncertainty_high_see: Optional[float] = None
    confidence_interval_pct: float = 95.0

    # Audit & Replicability
    formula_latex: str
    fallback_notes: List[str] = Field(default_factory=list)
    input_snapshot: Dict
