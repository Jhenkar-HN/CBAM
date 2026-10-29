from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema


class CNCodeBase(BaseModel):
    cn_code: str = Field(..., json_schema_extra={"example": "7318 15 82"}, description="8-digit CN code")
    description: str = Field(..., json_schema_extra={"example": "Other screws and bolts, whether or not with their nuts or washers"})
    sector: str = Field(default="Iron and Steel")
    includes_indirect_emissions: bool = Field(default=True, description="delta_CN flag for Scope 2")
    requires_precursors: bool = Field(default=True, description="Whether precursor materials must be embedded")
    default_unit: str = Field(default="tonne")
    notes: Optional[str] = None


class CNCodeCreate(CNCodeBase):
    pass


class CNCodeRead(CNCodeBase, BaseSchema):
    pass


class CBAMDefaultValueBase(BaseModel):
    category: str = Field(..., json_schema_extra={"example": "fuel"}, description="'fuel', 'electricity', 'precursor'")
    item_name: str = Field(..., json_schema_extra={"example": "Diesel"}, description="Name of fuel, energy carrier, or precursor")
    unit: str = Field(..., json_schema_extra={"example": "litre"})
    ncv_value: Optional[float] = Field(None, json_schema_extra={"example": 0.0357}, description="Net Calorific Value (e.g. GJ/litre)")
    ncv_unit: Optional[str] = Field(None, json_schema_extra={"example": "GJ/litre"})
    ef_value: float = Field(..., json_schema_extra={"example": 0.0741}, description="Emission factor (e.g. tCO2/GJ)")
    ef_unit: str = Field(..., json_schema_extra={"example": "tCO2/GJ"})
    oxidation_factor: float = Field(default=1.0)
    geographic_scope: str = Field(default="India / Global")
    source_reference: str = Field(..., json_schema_extra={"example": "IPCC 2006 Guidelines"})
    is_active: bool = True


class CBAMDefaultValueCreate(CBAMDefaultValueBase):
    pass


class CBAMDefaultValueRead(CBAMDefaultValueBase, BaseSchema):
    id: int
