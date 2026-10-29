import io
import fitz
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
import app.db.models  # Ensure all SQLAlchemy models are registered
from app.main import app
from app.modules.document_ai.parser import compute_sha256, parse_document
from app.modules.document_ai.extractor import mock_llm_schema_extraction, run_document_ai_extraction


# Set up isolated in-memory test database with StaticPool so all sessions share the in-memory database
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_compute_sha256():
    sample_bytes = b"Electricity Bill DHBVN 250000 kWh"
    h1 = compute_sha256(sample_bytes)
    h2 = compute_sha256(sample_bytes)
    assert h1 == h2
    assert len(h1) == 64


def test_parse_csv_spreadsheet():
    df = pd.DataFrame({
        "Month": ["Jan", "Feb"],
        "Diesel_Litres": [2500, 3100],
        "Electricity_kWh": [45000, 52000],
        "Production_tonnes": [120, 140]
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    sha, pages = parse_document(csv_bytes, "plant_energy_log.csv")

    assert len(sha) == 64
    assert len(pages) == 1
    assert "Diesel_Litres" in pages[0]["text"]
    assert "45000" in pages[0]["text"]


def test_schema_constrained_extraction():
    sample_text = """
    UTILITY POWER INVOICE
    Consumer: Apex Fasteners Unit 1
    Billing Cycle: October 2025
    Total Active Energy Consumption: 185,400 kWh
    Furnace Oil Dispatched: 12,500 litres
    Raw Material Wire Rod: 480 tonnes
    Net Output / Production: 450 tonnes
    """
    pages_data = [{"page_number": 1, "text": sample_text, "is_ocr": False}]
    candidates = mock_llm_schema_extraction(pages_data, "invoice.pdf")

    field_map = {c.field_name: c for c in candidates}

    assert "electricity_quantity" in field_map
    assert field_map["electricity_quantity"].extracted_value == 185400.0
    assert field_map["electricity_quantity"].unit == "KWH"
    assert "185,400 kWh" in field_map["electricity_quantity"].evidence_snippet

    assert "furnace_oil_quantity" in field_map
    assert field_map["furnace_oil_quantity"].extracted_value == 12500.0
    assert "12,500 litres" in field_map["furnace_oil_quantity"].evidence_snippet

    assert "precursor_steel_quantity" in field_map
    assert field_map["precursor_steel_quantity"].extracted_value == 480.0

    assert "production_quantity" in field_map
    assert field_map["production_quantity"].extracted_value == 450.0


def test_document_upload_and_override_api():
    # 1. Create in-memory synthetic PDF with text
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Active Energy Consumption: 320,000 kWh\nProduction Output: 600 tonnes")
    pdf_bytes = doc.write()
    doc.close()

    # 2. Upload to API endpoint
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("factory_bill.pdf", pdf_bytes, "application/pdf")},
        data={"workspace_id": "test_workspace_1"}
    )

    assert response.status_code == 201
    res_data = response.json()
    assert "document_hash" in res_data
    doc_hash = res_data["document_hash"]
    assert len(res_data["extracted_fields"]) >= 2

    # 3. Apply human-in-the-loop override
    override_payload = {
        "document_hash": doc_hash,
        "field_name": "electricity_quantity",
        "override_value": 315000.0,
        "override_unit": "kWh",
        "override_reason": "Adjusted for power factor penalty deducted in billing addendum",
        "user_id": "auditor_haris"
    }

    override_res = client.post("/api/v1/documents/override", json=override_payload)
    assert override_res.status_code == 200
    override_data = override_res.json()

    assert override_data["status"] == "success"
    assert override_data["was_overridden"] is True
    assert float(override_data["raw_value"]) == 320000.0
    assert float(override_data["effective_value"]) == 315000.0

    # 4. Query extracted fields endpoint
    fields_res = client.get(f"/api/v1/documents/{doc_hash}/fields")
    assert fields_res.status_code == 200
    fields_list = fields_res.json()
    elec_field = next(f for f in fields_list if f["field_name"] == "electricity_quantity")
    assert elec_field["was_overridden"] is True
    assert elec_field["user_override_value"] == "315000.0"
    assert elec_field["raw_extracted_value"] == "320000.0"
