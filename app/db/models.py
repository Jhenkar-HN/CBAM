import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, synonym
from app.db.database import Base


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class Company(Base):
    """Company / Enterprise representing the exporting entity."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    legal_name = Column(String(255), nullable=False, unique=True)
    country = Column(String(100), default="India")
    eori_number = Column(String(50), nullable=True)
    registration_number = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    installations = relationship("Installation", back_populates="company", cascade="all, delete-orphan")


class Installation(Base):
    """Specific manufacturing site / plant where emissions occur."""
    __tablename__ = "installations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    un_locode = Column(String(10), nullable=True)
    location = Column(String(255), nullable=False)
    country_code = Column(String(5), default="IN")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    company = relationship("Company", back_populates="installations")
    reporting_periods = relationship("ReportingPeriod", back_populates="installation", cascade="all, delete-orphan")


class CNCodeRegistry(Base):
    """Registry of EU CBAM covered 8-digit Combined Nomenclature (CN) codes."""
    __tablename__ = "cn_code_registry"

    cn_code = Column(String(20), primary_key=True, index=True)  # e.g. "7318 15 82"
    description = Column(String(500), nullable=False)
    sector = Column(String(100), default="Iron and Steel")
    includes_indirect_emissions = Column(Boolean, default=True)  # delta_CN
    requires_precursors = Column(Boolean, default=True)
    default_unit = Column(String(20), default="tonne")
    notes = Column(Text, nullable=True)

    # Relationships
    reporting_periods = relationship("ReportingPeriod", back_populates="cn_registry")


class CBAMDefaultValues(Base):
    """Standardized and versioned official default values for fuels, grid, and precursors."""
    __tablename__ = "cbam_default_values"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # 'fuel', 'electricity', 'precursor', 'process'
    item_name = Column(String(100), nullable=False)  # e.g. 'Diesel', 'Furnace Oil', 'Natural Gas', 'Indian Grid (CEA)', 'Crude Steel'
    unit = Column(String(30), nullable=False)  # 'litre', 'kg', 'Nm3', 'kWh', 'tonne'
    ncv_value = Column(Float, nullable=True)  # Net Calorific Value (e.g. GJ/tonne, MJ/kg)
    ncv_unit = Column(String(30), nullable=True)
    ef_value = Column(Float, nullable=False)  # Emission factor (e.g. tCO2/GJ, tCO2/MWh, tCO2/t)
    ef_unit = Column(String(30), nullable=False)
    oxidation_factor = Column(Float, default=1.0)
    geographic_scope = Column(String(100), default="India / Global")
    source_reference = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    cn_code = Column(String(20), nullable=True, index=True)  # Precursor defaults are keyed to a CN code
    markup_pct = Column(Float, nullable=True)  # Regulatory penalty markup applied to unverified defaults


class ReportingPeriod(Base):
    """A distinct compliance reporting period (e.g., Year 2025/2026) for an installation."""
    __tablename__ = "reporting_periods"

    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False)
    year = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_cn_code = Column(String(20), ForeignKey("cn_code_registry.cn_code"), nullable=False)
    status = Column(String(50), default="Draft")  # 'Draft', 'User-Confirmed', 'Expert-Reviewed', 'Externally Verified'
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    installation = relationship("Installation", back_populates="reporting_periods")
    cn_registry = relationship("CNCodeRegistry", back_populates="reporting_periods")
    uploaded_files = relationship("UploadedFile", back_populates="reporting_period", cascade="all, delete-orphan")
    production_data = relationship("ProductionData", back_populates="reporting_period", uselist=False, cascade="all, delete-orphan")
    calculation_results = relationship("CalculationResult", back_populates="reporting_period", cascade="all, delete-orphan")
    audit_trail = relationship("AuditTrail", back_populates="reporting_period", cascade="all, delete-orphan")


class DocumentRecord(Base):
    """Document metadata record indexed by cryptographic SHA-256 hash."""
    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)
    document_hash = Column(String(64), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    workspace_id = Column(String(100), nullable=False, index=True)
    page_count = Column(Integer, default=1)
    file_size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    extracted_fields = relationship("ExtractedFieldAudit", back_populates="document_record", cascade="all, delete-orphan")


class UploadedFile(Base):
    """File uploaded by the user with cryptographic SHA-256 hash for tamper evidence."""
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    reporting_period_id = Column(Integer, ForeignKey("reporting_periods.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    doc_category = Column(String(50), nullable=True)
    upload_timestamp = Column(DateTime, default=utc_now)

    # Relationships
    reporting_period = relationship("ReportingPeriod", back_populates="uploaded_files")


class ExtractedFieldAudit(Base):
    """Audit ledger entry for Document AI extracted field, preserving raw and user-override values."""
    __tablename__ = "extracted_fields_audit"

    id = Column(Integer, primary_key=True, index=True)
    document_hash = Column(String(64), ForeignKey("document_records.document_hash"), nullable=True, index=True)
    reporting_period_id = Column(Integer, ForeignKey("reporting_periods.id"), nullable=True)
    field_name = Column(String(100), nullable=False)
    field_category = Column(String(50), nullable=True, default="scope1_fuel")

    # Raw Model Extraction
    raw_extracted_value = Column(String(100), nullable=True)
    raw_unit = Column(String(30), nullable=True)
    raw_extracted_unit = synonym("raw_unit")
    confidence_score = Column(Float, default=0.85)
    evidence_page = Column(Integer, default=1)
    evidence_snippet = Column(Text, nullable=True)

    # Effective / Override Values
    effective_value = Column(String(100), nullable=True)
    effective_unit = Column(String(30), nullable=True)
    was_overridden = Column(Boolean, default=False)
    user_override_value = Column(String(100), nullable=True)
    user_override_unit = Column(String(30), nullable=True)
    modified_by_user_id = Column(String(100), nullable=True)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    document_record = relationship("DocumentRecord", back_populates="extracted_fields")


class ProductionData(Base):
    """Net production and shared facility multi-product allocation parameters."""
    __tablename__ = "production_data"

    id = Column(Integer, primary_key=True, index=True)
    reporting_period_id = Column(Integer, ForeignKey("reporting_periods.id"), unique=True, nullable=False)
    target_product_family = Column(String(255), nullable=False)
    target_production_tonnes = Column(Float, nullable=False)
    total_facility_production_tonnes = Column(Float, nullable=False)
    allocation_factor_alpha = Column(Float, nullable=False)
    scrap_tonnes = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    reporting_period = relationship("ReportingPeriod", back_populates="production_data")


class CalculationResult(Base):
    """Deterministic calculation output with complete transparency freeze and uncertainty bounds."""
    __tablename__ = "calculation_results"

    id = Column(Integer, primary_key=True, index=True)
    reporting_period_id = Column(Integer, ForeignKey("reporting_periods.id"), nullable=False)
    scope1_direct_tco2 = Column(Float, nullable=False)
    scope2_indirect_tco2 = Column(Float, nullable=False)
    precursor_emissions_tco2 = Column(Float, nullable=False)
    total_embedded_emissions_tco2 = Column(Float, nullable=False)
    specific_embedded_emissions_see = Column(Float, nullable=False)
    see_unit = Column(String(20), default="tCO2/t")
    includes_indirect = Column(Boolean, nullable=False)

    # Uncertainty Quantification
    uncertainty_low_see = Column(Float, nullable=True)
    uncertainty_high_see = Column(Float, nullable=True)
    confidence_interval_pct = Column(Float, default=95.0)

    # Audit & Replicability
    formula_applied = Column(Text, nullable=False)
    input_snapshot_json = Column(Text, nullable=False)
    status = Column(String(50), default="Calculated")
    calculation_timestamp = Column(DateTime, default=utc_now)

    # Relationships
    reporting_period = relationship("ReportingPeriod", back_populates="calculation_results")


class AuditTrail(Base):
    """Immutable audit trail for all operations performed in the reporting workspace."""
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    reporting_period_id = Column(Integer, ForeignKey("reporting_periods.id"), nullable=True)
    action = Column(String(100), nullable=False)
    performed_by = Column(String(100), default="System")
    timestamp = Column(DateTime, default=utc_now)
    details_json = Column(Text, nullable=True)

    # Relationships
    reporting_period = relationship("ReportingPeriod", back_populates="audit_trail")
