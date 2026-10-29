"""Unit tests verifying Stage 5 Regulatory RAG assistant and ReportLab PDF/CSV generators."""

from fastapi.testclient import TestClient
import pytest
from app.config import settings
from app.main import app
from app.modules.rag.assistant import answer_regulatory_query
from app.modules.rag.indexer import get_vector_store
from app.modules.reporting.csv_generator import generate_passport_csv
from app.modules.reporting.pdf_generator import generate_passport_pdf
from app.schemas.rag import RAGQueryRequest

client = TestClient(app)

SAMPLE_PASSPORT_DATA = {
    "workspace": {
        "company_name": "Apex Fasteners Pvt Ltd",
        "installation_name": "Apex Unit 1 - Cold Forging",
        "installation_id": "IN-FDB-001",
        "country": "India",
        "cn_code": "7318 15 82",
        "reporting_period": "2026 (Annual)",
        "target_product_family": "Steel Fasteners (CN 7318 15 82)",
    },
    "calculation": {
        "specific_embedded_emissions_see": 2.2851,
        "facility_gross_scope1_tco2": 46.6722,
        "allocated_scope1_direct_tco2": 37.3378,
        "facility_gross_scope2_tco2": 179.0,
        "allocated_scope2_indirect_tco2": 143.2000,
        "precursor_emissions_tco2": 962.0000,
        "total_embedded_emissions_tco2": 1142.5378,
        "net_target_production_tonnes": 500.0,
        "allocation_factor_alpha": 0.80,
        "includes_indirect_delta_cn": True,
        "data_quality_rating": "ACTUAL_PRIMARY",
        "uncertainty": {
            "p5": 2.1520,
            "p50": 2.2840,
            "p95": 2.4210,
            "iterations": 5000,
        },
        "formula_latex": r"\text{SEE} = \frac{37.3378 + 143.2000 + 962.0000}{500.00} = 2.2851\text{ tCO}_2/\text{t}",
    },
    "uploaded_documents": {
        "57899e573e33a04fec4c0847b357e3e0cee07592dac1caf96ff452f519a927c9": {
            "filename": "DHBVN_Electricity_Oct2026.pdf",
            "file_size_bytes": 145920,
            "extracted_fields": [
                {
                    "field_name": "electricity_quantity",
                    "extracted_value": 250000.0,
                    "unit": "kWh",
                    "confidence_score": 0.96,
                }
            ],
        }
    },
}


# =====================================================================
# 1. Regulatory RAG Tests
# =====================================================================

def test_rag_vector_store_indexing():
    store = get_vector_store()
    assert len(store.chunks) >= 3
    # Verify chunks have metadata
    first_chunk = store.chunks[0]
    assert first_chunk.document_title != ""
    assert first_chunk.publication_year >= 2024
    assert len(first_chunk.text) > 20


def test_rag_query_precursor_guidance():
    req = RAGQueryRequest(query="What are the rules for precursor materials in steel fasteners?", top_k=3)
    resp = answer_regulatory_query(req)
    assert len(resp.citations) >= 1
    assert "7318" in resp.answer or "precursor" in resp.answer.lower()
    assert any("complex goods" in c.excerpt.lower() or "precursor" in c.excerpt.lower() for c in resp.citations)


def test_rag_query_electricity_grid_factor():
    req = RAGQueryRequest(query="Which electricity emission factor should Indian exporters use under CBAM?", top_k=2)
    resp = answer_regulatory_query(req)
    assert len(resp.citations) >= 1
    assert "CEA" in resp.answer or "0.716" in resp.answer or "grid" in resp.answer.lower()


def test_rag_strict_hallucination_guardrail():
    # An entirely unrelated, out-of-domain question should trigger the refusal guardrail
    req = RAGQueryRequest(query="What is the recipe for baking chocolate sourdough croissants?", top_k=2)
    resp = answer_regulatory_query(req)
    assert "Information not found in the indexed official EC material" in resp.answer
    assert len(resp.citations) == 0


# =====================================================================
# 2. PDF & CSV Report Generator Tests
# =====================================================================

def test_generate_passport_pdf():
    pdf_bytes = generate_passport_pdf(SAMPLE_PASSPORT_DATA)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Standard PDF magic byte header check
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_passport_csv():
    csv_text = generate_passport_csv(SAMPLE_PASSPORT_DATA)
    assert isinstance(csv_text, str)
    assert "# CBAM-READY EMISSIONS PASSPORT" in csv_text
    assert "Apex Fasteners Pvt Ltd" in csv_text
    assert "7318 15 82" in csv_text
    assert "2.2851" in csv_text
    assert "57899e573e33a04fec4c0847b357e3e0cee07592dac1caf96ff452f519a927c9" in csv_text


# =====================================================================
# 3. FastAPI Endpoint Integration Tests
# =====================================================================

def test_api_rag_query():
    resp = client.post(
        "/api/v1/rag/query",
        json={"query": "What is the penalty markup for default values?", "top_k": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data


def test_api_download_passport_pdf():
    resp = client.post("/api/v1/passport/download-pdf", json=SAMPLE_PASSPORT_DATA)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=CBAM_Passport_" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")


def test_api_download_passport_csv():
    resp = client.post("/api/v1/passport/download-csv", json=SAMPLE_PASSPORT_DATA)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "CBAM-READY EMISSIONS PASSPORT" in resp.text
