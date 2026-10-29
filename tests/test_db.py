"""Unit test verifying Stage 1 database schema, relationships, and seed data."""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.db.models import (
    Company,
    Installation,
    ReportingPeriod,
    CNCodeRegistry,
    CBAMDefaultValues,
    ExtractedFieldAudit,
    ProductionData,
    CalculationResult,
)


@pytest.fixture(scope="module")
def db_session():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()

    cn_codes = [
        CNCodeRegistry(
            cn_code="7318 15 82",
            description="Other screws and bolts, of steel",
            sector="Iron and Steel",
            includes_indirect_emissions=True,
            requires_precursors=True,
            default_unit="tonne",
        )
    ]
    default_factors = [
        CBAMDefaultValues(
            category="fuel",
            item_name="Furnace Oil",
            unit="litre",
            ncv_value=0.0402,
            ncv_unit="GJ/litre",
            ef_value=0.0774,
            ef_unit="tCO2/GJ",
            oxidation_factor=1.0,
            source_reference="IPCC 2006",
        ),
        CBAMDefaultValues(
            category="electricity",
            item_name="Indian National Grid",
            unit="kWh",
            ef_value=0.716,
            ef_unit="tCO2/MWh",
            source_reference="CEA v19",
        ),
    ]
    session.add_all(cn_codes)
    session.add_all(default_factors)
    session.commit()

    yield session
    session.close()


def test_cn_code_registry_seeded(db_session):
    fastener_code = db_session.query(CNCodeRegistry).filter_by(cn_code="7318 15 82").first()
    assert fastener_code is not None
    assert fastener_code.includes_indirect_emissions is True  # delta_CN = 1
    assert fastener_code.requires_precursors is True


def test_default_values_seeded(db_session):
    fuel = db_session.query(CBAMDefaultValues).filter_by(item_name="Furnace Oil").first()
    assert fuel is not None
    assert fuel.ncv_value == 0.0402
    assert fuel.ef_value == 0.0774

    grid = db_session.query(CBAMDefaultValues).filter_by(category="electricity").first()
    assert grid is not None
    assert grid.ef_value > 0


def test_company_installation_lifecycle(db_session):
    unique_name = f"Test Fasteners India {uuid.uuid4().hex[:6]}"
    company = Company(
        legal_name=unique_name,
        country="India",
        eori_number="IN9988776655",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    installation = Installation(
        company_id=company.id,
        name="Unit 1 Plant",
        location="Pune, Maharashtra",
        country_code="IN",
    )
    db_session.add(installation)
    db_session.commit()
    db_session.refresh(installation)

    assert installation.id is not None
    assert len(company.installations) == 1
    assert company.installations[0].name == "Unit 1 Plant"


def test_extracted_field_effective_value():
    field = ExtractedFieldAudit(
        field_name="electricity_consumption",
        field_category="scope2_electricity",
        raw_extracted_value="1000.0",
        raw_unit="kWh",
        user_override_value="1250.0",
        user_override_unit="kWh",
        effective_value="1250.0",
        effective_unit="kWh",
        was_overridden=True
    )
    assert field.effective_value == "1250.0"
    assert field.was_overridden is True

    field_no_override = ExtractedFieldAudit(
        field_name="diesel_litres",
        field_category="scope1_fuel",
        raw_extracted_value="500.0",
        raw_unit="litre",
        effective_value="500.0",
        effective_unit="litre",
        was_overridden=False
    )
    assert field_no_override.effective_value == "500.0"
    assert field_no_override.was_overridden is False
