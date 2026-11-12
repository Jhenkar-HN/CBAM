"""Auditable CBAM Emissions Evidence Ledger CSV Exporter."""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def generate_passport_csv(passport_data: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    """
    Generates a structured, machine-readable CSV audit ledger containing:
    1. Workspace & installation metadata.
    2. Subtotal emission calculations and Specific Embedded Emissions (SEE).
    3. Itemized activity data inputs with SHA-256 cryptographic hashes and override history.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    ws = passport_data.get("workspace", {})
    calc = passport_data.get("calculation", {})
    unc = calc.get("uncertainty", {})

    # Section 1: Metadata Header
    writer.writerow(["# CBAM-READY EMISSIONS PASSPORT - AUDIT EVIDENCE LEDGER"])
    writer.writerow(["# Generated At", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")])
    writer.writerow(["# Legal Basis", "Regulation (EU) 2023/956 & Implementing Regulation (EU) 2025/2621"])
    writer.writerow([])

    writer.writerow(["PARAMETER", "VALUE", "UNIT", "NOTES"])
    writer.writerow(["Company Name", ws.get("company_name", ""), "", "Exporting Entity"])
    writer.writerow(["Installation Name", ws.get("installation_name", ""), "", "Manufacturing Site"])
    writer.writerow(["Installation ID", ws.get("installation_id", ""), "", "UN/LOCODE or Local ID"])
    writer.writerow(["Country of Origin", ws.get("country", ""), "", "ISO 3166-1"])
    writer.writerow(["Target Product Family", ws.get("target_product_family", ""), "", "Covered Goods"])
    writer.writerow(["Target CN Code", ws.get("cn_code", ""), "", "Combined Nomenclature 8-digit"])
    writer.writerow(["Scope 2 Included (delta_CN)", 1 if calc.get("includes_indirect_delta_cn") else 0, "flag", "1 = included, 0 = exempt"])
    writer.writerow(["Mass Allocation Factor (alpha_p)", f"{calc['allocation_factor_alpha']:.6f}", "ratio", "Target Production / Total Plant Output"])
    writer.writerow(["Net Target Production", f"{calc['net_target_production_tonnes']:.4f}", "tonne", "Divisor for SEE denominator"])
    writer.writerow(["Data Quality Classification", calc["data_quality_rating"], "", "ACTUAL_PRIMARY / FALLBACK_DEFAULT / HYBRID"])
    writer.writerow([])

    # Section 2: Calculated Specific Embedded Emissions
    writer.writerow(["# CARBON BALANCE & EMBEDDED EMISSIONS SUMMARY"])
    writer.writerow(["EMISSION_COMPONENT", "GROSS_FACILITY_tCO2", "ALLOCATION_FACTOR", "ALLOCATED_PRODUCT_tCO2", "SPECIFIC_tCO2e_PER_TONNE"])

    target_t = calc["net_target_production_tonnes"]
    alloc_scope1 = calc["allocated_scope1_direct_tco2"]
    alloc_scope2 = calc["allocated_scope2_indirect_tco2"]
    precursor_val = calc["precursor_emissions_tco2"]
    total_embedded = calc["total_embedded_emissions_tco2"]
    see_val = calc["specific_embedded_emissions_see"]
    alpha_p = calc["allocation_factor_alpha"]

    writer.writerow(["Direct Scope 1 (Combustion/Process)", f"{calc['facility_gross_scope1_tco2']:.4f}", f"{alpha_p:.4f}", f"{alloc_scope1:.4f}", f"{alloc_scope1 / target_t:.6f}"])
    writer.writerow(["Indirect Scope 2 (Grid Electricity)", f"{calc['facility_gross_scope2_tco2']:.4f}", f"{alpha_p:.4f}", f"{alloc_scope2:.4f}", f"{alloc_scope2 / target_t:.6f}"])
    writer.writerow(["Precursor Embedded Emissions (Wire Rod)", f"{precursor_val:.4f}", "1.0000", f"{precursor_val:.4f}", f"{precursor_val / target_t:.6f}"])
    writer.writerow(["TOTAL EMBEDDED EMISSIONS", "—", "—", f"{total_embedded:.4f}", f"{see_val:.6f}"])
    writer.writerow([])

    # Section 3: Uncertainty Quantification (Monte Carlo)
    writer.writerow(["# MONTE CARLO UNCERTAINTY QUANTIFICATION (5,000 ITERATIONS)"])
    writer.writerow(["PERCENTILE", "VALUE_tCO2e_PER_TONNE", "DESCRIPTION"])
    writer.writerow(["P5", f"{unc['p5']:.6f}" if unc else "", "Conservative Lower Bound (5th percentile)"])
    writer.writerow(["P50", f"{unc['p50']:.6f}" if unc else "", "Simulated Median (50th percentile)"])
    writer.writerow(["P95", f"{unc['p95']:.6f}" if unc else "", "Conservative Upper Bound (95th percentile)"])
    writer.writerow([])

    # Section 4: Activity Data Provenance & Cryptographic Ledger
    writer.writerow(["# ACTIVITY DATA PROVENANCE & CRYPTOGRAPHIC FILE LEDGER"])
    writer.writerow(["SOURCE_STREAM", "RAW_VALUE", "RAW_UNIT", "EFFECTIVE_VALUE", "EFFECTIVE_UNIT", "WAS_OVERRIDDEN", "OVERRIDE_REASON", "FILE_NAME", "SHA256_HASH_DIGEST"])

    docs = passport_data.get("uploaded_documents", {})
    overrides = passport_data.get("overrides") or {}
    if docs:
        for doc_hash, doc in docs.items():
            for f in doc.get("extracted_fields", []):
                field_name = f.get("field_name", "")
                raw_value = f.get("extracted_value", "")
                raw_unit = f.get("unit", "")
                override = overrides.get(f"{doc_hash}_{field_name}") or {}
                if override:
                    effective_value = override.get("override_value", raw_value)
                    effective_unit = override.get("override_unit") or raw_unit
                    was_overridden = "True"
                    override_reason = override.get("override_reason") or "Human override"
                else:
                    effective_value = raw_value
                    effective_unit = raw_unit
                    was_overridden = "False"
                    override_reason = "No override applied"
                writer.writerow([
                    field_name,
                    raw_value,
                    raw_unit,
                    effective_value,
                    effective_unit,
                    was_overridden,
                    override_reason,
                    doc.get("filename", ""),
                    doc_hash,
                ])
    else:
        writer.writerow(["No uploaded source records", "", "", "", "", "", "", "", ""])

    csv_content = output.getvalue()
    output.close()

    if output_path:
        output_path.write_text(csv_content, encoding="utf-8")

    return csv_content
