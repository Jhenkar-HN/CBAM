import re
from typing import List
from app.schemas.document import DocumentExtractionResult, ExtractedFieldCandidate


def find_snippet_context(full_text: str, target_match_str: str, window: int = 50) -> str:
    """Finds the surrounding text snippet context for a given extracted value for audit verification."""
    if not target_match_str:
        return ""
    str_val = re.escape(str(target_match_str))
    match = re.search(str_val, full_text, re.IGNORECASE)
    if match:
        start = max(0, match.start() - window)
        end = min(len(full_text), match.end() + window)
        snippet = full_text[start:end].replace("\n", " ").strip()
        return f"...{snippet}..."
    return f"Value '{target_match_str}' extracted from document text."


def mock_llm_schema_extraction(pages_data: List[dict], filename: str) -> List[ExtractedFieldCandidate]:
    """
    Schema-constrained extraction engine (heuristic regex baseline with snippet anchors).
    Extracts dates, quantities, units, and activity types with page and verbatim snippet references.
    """
    candidates = []
    combined_text = "\n".join([p["text"] for p in pages_data])

    # 1. Electricity / Grid Consumption
    kwh_match = re.search(r'(\d+[\d,]*\.?\d*)\s*(kWh|MWh|units)', combined_text, re.IGNORECASE)
    if not kwh_match:
        kwh_match = re.search(r'(?:electricity|power|consumption|active\s*energy)[\w\s:=-]*?(\d+[\d,]*\.?\d*)\s*(kWh|MWh|units)', combined_text, re.IGNORECASE)

    if kwh_match:
        val_str = kwh_match.group(1).replace(',', '')
        val = float(val_str)
        unit = kwh_match.group(2).upper()
        if unit == "UNITS":
            unit = "kWh"

        page_num = 1
        for p in pages_data:
            if kwh_match.group(0) in p["text"]:
                page_num = p["page_number"]
                break

        candidates.append(
            ExtractedFieldCandidate(
                field_name="electricity_quantity",
                extracted_value=val,
                unit=unit,
                confidence_score=0.92,
                evidence_page=page_num,
                evidence_snippet=find_snippet_context(combined_text, kwh_match.group(0)),
                field_category="scope2_electricity",
            )
        )

    # 2. Fuel / Furnace Oil / Diesel
    # Pattern A: "12,500 litres of Furnace Oil"
    fuel_match = re.search(
        r'(\d+[\d,]*\.?\d*)\s*(liters|litres|L|m3|tonnes|kg|GJ)\s*(?:of\s*)?(diesel|hsd|furnace\s*oil|natural\s*gas|fuel|lpg)',
        combined_text,
        re.IGNORECASE,
    )
    # Pattern B: "Furnace Oil Dispatched: 12,500 litres"
    if not fuel_match:
        fuel_match = re.search(
            r'(diesel|hsd|furnace\s*oil|natural\s*gas|fuel|lpg)[\w\s:=-]*?(\d+[\d,]*\.?\d*)\s*(liters|litres|L|m3|tonnes|kg|GJ)',
            combined_text,
            re.IGNORECASE,
        )
        if fuel_match:
            fuel_type = fuel_match.group(1).lower().strip()
            val = float(fuel_match.group(2).replace(',', ''))
            unit = fuel_match.group(3).lower()
            fuel_field_name = "furnace_oil_quantity" if "furnace" in fuel_type else "fuel_quantity"
            candidates.append(
                ExtractedFieldCandidate(
                    field_name=fuel_field_name,
                    extracted_value=val,
                    unit=unit,
                    confidence_score=0.89,
                    evidence_page=1,
                    evidence_snippet=find_snippet_context(combined_text, fuel_match.group(0)),
                    field_category="scope1_fuel",
                )
            )
    else:
        val = float(fuel_match.group(1).replace(',', ''))
        unit = fuel_match.group(2).lower()
        fuel_type = fuel_match.group(3).lower().strip()
        fuel_field_name = "furnace_oil_quantity" if "furnace" in fuel_type else "fuel_quantity"
        candidates.append(
            ExtractedFieldCandidate(
                field_name=fuel_field_name,
                extracted_value=val,
                unit=unit,
                confidence_score=0.88,
                evidence_page=1,
                evidence_snippet=find_snippet_context(combined_text, fuel_match.group(0)),
                field_category="scope1_fuel",
            )
        )

    # 3. Precursor Material (Steel Wire Rod / Bars)
    precursor_match = re.search(
        r'(?:wire\s*rod|raw\s*material|precursor|steel\s*bar)[\w\s:.,\-/()=]*?(\d+[\d,]*\.?\d*)\s*(tonnes|MT|kg)',
        combined_text,
        re.IGNORECASE,
    )
    if precursor_match:
        val = float(precursor_match.group(1).replace(',', ''))
        unit = precursor_match.group(2).upper()
        candidates.append(
            ExtractedFieldCandidate(
                field_name="precursor_steel_quantity",
                extracted_value=val,
                unit=unit,
                confidence_score=0.90,
                evidence_page=1,
                evidence_snippet=find_snippet_context(combined_text, precursor_match.group(0)),
                field_category="precursor",
            )
        )

    # Supplier-declared specific embedded emissions for a precursor.
    precursor_see_match = re.search(
        r'(?:(?:specific\s+embedded\s+emissions|embedded\s+emissions|supplier_specific_emissions|precursor\s+SEE|\bSEE)[\w\s:.,\-/()=]*?)?(\d+[\d,]*\.?\d*)\s*(t\s*CO2e?\s*/\s*(?:t|tonne))',
        combined_text,
        re.IGNORECASE,
    )
    if precursor_see_match:
        candidates.append(
            ExtractedFieldCandidate(
                field_name="precursor_see",
                extracted_value=float(precursor_see_match.group(1).replace(',', '')),
                unit="tCO2/t",
                confidence_score=0.90,
                evidence_page=1,
                evidence_snippet=find_snippet_context(combined_text, precursor_see_match.group(0)),
                field_category="precursor",
            )
        )

    # 4. Net Production Quantity
    prod_match = re.search(
        r'(?:production|output|net\s*quantity|manufactured)[\w\s:=-]*?(\d+[\d,]*\.?\d*)\s*(tonnes|MT|kg)',
        combined_text,
        re.IGNORECASE,
    )
    if prod_match:
        val = float(prod_match.group(1).replace(',', ''))
        unit = prod_match.group(2).upper()
        candidates.append(
            ExtractedFieldCandidate(
                field_name="production_quantity",
                extracted_value=val,
                unit=unit,
                confidence_score=0.95,
                evidence_page=1,
                evidence_snippet=find_snippet_context(combined_text, prod_match.group(0)),
                field_category="production",
            )
        )

    return candidates


def run_document_ai_extraction(file_bytes: bytes, filename: str) -> DocumentExtractionResult:
    """Combines parsing, hashing, and schema-constrained extraction."""
    from app.modules.document_ai.parser import parse_document

    sha256_hash, pages_data = parse_document(file_bytes, filename)
    extracted_fields = mock_llm_schema_extraction(pages_data, filename)

    return DocumentExtractionResult(
        document_hash=sha256_hash,
        filename=filename,
        page_count=len(pages_data),
        extracted_fields=extracted_fields,
        raw_text_by_page=pages_data,
    )
