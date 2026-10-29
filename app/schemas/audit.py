from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema


class AuditLogCreate(BaseModel):
    reporting_period_id: Optional[int] = None
    action: str = Field(..., json_schema_extra={"example": "FIELD_OVERRIDDEN"})
    performed_by: str = Field(default="Auditor")
    details_json: Optional[str] = None


class AuditLogRead(BaseSchema):
    id: int
    reporting_period_id: Optional[int]
    action: str
    performed_by: str
    timestamp: datetime
    details_json: Optional[str]
