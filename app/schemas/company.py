from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema, ReviewStatus


class CompanyBase(BaseModel):
    legal_name: str
    country: str
    eori_number: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class InstallationBase(BaseModel):
    name: str
    un_locode: Optional[str] = None
    location: str
    country_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InstallationCreate(InstallationBase):
    company_id: int


class ReportingPeriodBase(BaseModel):
    year: int
    start_date: date = Field(...)
    end_date: date = Field(...)
    target_cn_code: str
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
