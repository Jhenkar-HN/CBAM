from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema, ReviewStatus


class CompanyBase(BaseModel):
    legal_name: str = Field(..., json_schema_extra={"example": "Apex Fasteners Pvt Ltd"})
    country: str = Field(default="India")
    eori_number: Optional[str] = Field(None, json_schema_extra={"example": "IN1234567890"})
    registration_number: Optional[str] = Field(None, json_schema_extra={"example": "U28991DL2010PTC200100"})
    address: Optional[str] = Field(None, json_schema_extra={"example": "Plot 42, Sector 58, Faridabad, Haryana, India"})
    contact_email: Optional[str] = Field(None, json_schema_extra={"example": "compliance@apexfasteners.in"})


class CompanyCreate(CompanyBase):
    pass


class InstallationBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Apex Unit 1 - Cold Forging Plant"})
    un_locode: Optional[str] = Field(None, json_schema_extra={"example": "IN FDB"})
    location: str = Field(..., json_schema_extra={"example": "Faridabad, Haryana"})
    country_code: str = Field(default="IN")
    latitude: Optional[float] = Field(None, json_schema_extra={"example": 28.3670})
    longitude: Optional[float] = Field(None, json_schema_extra={"example": 77.3178})


class InstallationCreate(InstallationBase):
    company_id: int


class ReportingPeriodBase(BaseModel):
    year: int = Field(..., json_schema_extra={"example": 2025})
    start_date: date = Field(...)
    end_date: date = Field(...)
    target_cn_code: str = Field(..., json_schema_extra={"example": "7318 15 82"})
    status: ReviewStatus = Field(default=ReviewStatus.DRAFT)


class ReportingPeriodCreate(ReportingPeriodBase):
    installation_id: int


class ReportingPeriodRead(ReportingPeriodBase, BaseSchema):
    id: int
    installation_id: int
    created_at: datetime
    updated_at: datetime


class InstallationRead(InstallationBase, BaseSchema):
    id: int
    company_id: int
    created_at: datetime
    reporting_periods: List[ReportingPeriodRead] = []


class CompanyRead(CompanyBase, BaseSchema):
    id: int
    created_at: datetime
    installations: List[InstallationRead] = []
