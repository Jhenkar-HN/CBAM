"""Smoke test verifying Streamlit views and state management logic."""

from unittest.mock import patch
import pytest
from app.modules.calculation.engine import calculate_product_see
from app.modules.document_ai.extractor import run_document_ai_extraction
from frontend.views.dashboard import gather_effective_inputs


def test_gather_effective_inputs_defaults():
    with patch("streamlit.session_state", {}):
        req = gather_effective_inputs()
        assert req.cn_code == "7318 15 82"
        assert req.production.target_production_quantity == 500.0
        assert req.production.total_facility_production_quantity == 625.0
        assert len(req.fuels) == 1
        assert req.electricity is not None
        assert len(req.precursors) == 1


def test_full_pipeline_mock_run():
    # 1. Mock document extraction
    doc_text = "DHBVN Power Bill - Active Energy Consumption: 250,000 kWh\nFurnace Oil: 15,000 litres\nPrecursor: 520 tonnes\nProduction: 500 tonnes"
    res = run_document_ai_extraction(doc_text.encode("utf-8"), "plant_records.csv")
    assert len(res.extracted_fields) >= 3

    # 2. Gather inputs and calculate
    with patch("streamlit.session_state", {
        "uploaded_documents": {res.document_hash: {"extracted_fields": [f.model_dump() for f in res.extracted_fields]}},
        "field_overrides": {},
        "allocation_data": {"target_production_tonnes": 500.0, "total_facility_production_tonnes": 625.0, "apply_allocation_to_shared_energy": True},
    }):
        req = gather_effective_inputs()
        calc_result = calculate_product_see(req)
        assert calc_result.specific_embedded_emissions_see > 0
        assert calc_result.allocation_factor_alpha == 0.8
