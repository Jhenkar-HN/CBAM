from enum import Enum
from pydantic import BaseModel, ConfigDict


class ReviewStatus(str, Enum):
    DRAFT = "Draft"
    USER_CONFIRMED = "User-Confirmed"
    EXPERT_REVIEWED = "Expert-Reviewed"
    EXTERNALLY_VERIFIED = "Externally Verified"


class FieldCategory(str, Enum):
    SCOPE1_FUEL = "scope1_fuel"
    SCOPE2_ELECTRICITY = "scope2_electricity"
    PRODUCTION = "production"
    PRECURSOR = "precursor"


class DocCategory(str, Enum):
    ELECTRICITY_BILL = "electricity_bill"
    FUEL_INVOICE = "fuel_invoice"
    PRODUCTION_LOG = "production_log"
    SHIPPING_BILL = "shipping_bill"
    MILL_TEST_CERT = "mill_test_cert"
    OTHER = "other"


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
