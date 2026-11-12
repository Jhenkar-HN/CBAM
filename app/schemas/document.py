from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema, DocCategory, FieldCategory


class ExtractedFieldCandidate(BaseModel):
    """Pydantic schema used to constrain extraction from raw OCR/PDF/spreadsheet text."""
    field_name: str = Field(..., description="Standardized parameter name e.g. 'electricity_quantity', 'fuel_quantity', 'production_quantity'")
    extracted_value: float = Field(..., description="Numeric quantity extracted from the document")
    unit: str = Field(..., description="Physical unit (e.g. 'kWh', 'MWh', 'litre', 'kg', 'tonnes')")
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Extraction confidence score")
    evidence_page: int = Field(default=1, description="1-indexed page number in the source document")
    evidence_snippet: str = Field(..., description="Verbatim text excerpt containing the extracted value for human audit")
    bounding_box: Optional[str] = Field(None, description="Coordinates or zone if OCR provides bounding geometry")
    field_category: Optional[str] = Field(default="scope1_fuel", description="Category of emission source")


class DocumentExtractionResult(BaseModel):
    """Container schema for document parsing and extraction results."""
    document_hash: str = Field(..., description="SHA-256 cryptographic digest of document bytes")
    filename: str = Field(..., description="Original filename of the ingested document")
    page_count: int = Field(..., description="Total pages or sheets parsed")
    extracted_fields: List[ExtractedFieldCandidate] = Field(default_factory=list)


class HumanOverrideRequest(BaseModel):
    """Payload for human-in-the-loop field correction and audit logging."""
    document_hash: str = Field(..., description="SHA-256 hash of the target document")
    field_name: str = Field(..., description="Name of the field being overridden")
    override_value: float = Field(..., description="Corrected numerical value")
    override_unit: Optional[str] = Field(None, description="Corrected unit if different")
    override_reason: str = Field(..., description="Mandatory justification for audit compliance")
    user_id: str = Field(..., description="Identifier of the user applying the override")


class DocumentRecordRead(BaseSchema):
    id: int
    document_hash: str
    filename: str
    workspace_id: str
    page_count: int
    file_size_bytes: int
    created_at: datetime


class ExtractedFieldAuditRead(BaseSchema):
    id: int
    document_hash: str
    field_name: str
    raw_extracted_value: Optional[str]
    raw_unit: Optional[str]
    confidence_score: float
    evidence_page: Optional[int]
    evidence_snippet: Optional[str]
    effective_value: Optional[str]
    effective_unit: Optional[str]
    was_overridden: bool
    user_override_value: Optional[str]
    user_override_unit: Optional[str]
    modified_by_user_id: Optional[str]
    override_reason: Optional[str]
    created_at: datetime
