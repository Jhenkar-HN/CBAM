"""Generate clearly-labelled synthetic test fixtures for the upload pipeline.

These are NOT invoices and NOT valid records. Every page carries a TEST DATA
banner and placeholder identifiers so they cannot be mistaken for real
commercial documents. Their only purpose is exercising the extractor.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"

BANNER = "TEST DATA - SYNTHETIC FIXTURE - NOT A REAL DOCUMENT"
ISSUER = "Example Fasteners (Test) Pvt Ltd"
IDENTIFIERS = (
    "Placeholder address: Test Plot 00, Example Industrial Area<br/>"
    "Placeholder ID: EXAMPLE-ONLY-000 | Installation: TEST-INSTALL-001<br/>"
    "Reporting period: 01 January 2026 to 31 March 2026"
)

styles = getSampleStyleSheet()
banner_style = ParagraphStyle(
    "Banner", parent=styles["Normal"], fontSize=11, leading=14,
    textColor=colors.HexColor("#7F1D1D"), alignment=1, spaceAfter=6,
)
title_style = ParagraphStyle(
    "TitleX", parent=styles["Heading1"], fontSize=14, leading=18, spaceAfter=4,
)
body_style = ParagraphStyle(
    "BodyX", parent=styles["Normal"], fontSize=9.5, leading=13,
)
note_style = ParagraphStyle(
    "NoteX", parent=styles["Normal"], fontSize=8, leading=11,
    textColor=colors.HexColor("#475569"),
)


def _table(rows: list[list[str]], widths: list[float] | None = None) -> Table:
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build(filename: str, title: str, intro: list[str], rows: list[list[str]], closing: list[str]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"{BANNER} - {title}",
    )
    story = [
        Paragraph(BANNER, banner_style),
        Paragraph(title, title_style),
        Paragraph(ISSUER, body_style),
        Paragraph(IDENTIFIERS, note_style),
        Spacer(1, 8),
    ]
    story += [Paragraph(text, body_style) for text in intro]
    story.append(Spacer(1, 6))
    story.append(_table(rows))
    story += [Spacer(1, 6)] + [Paragraph(text, note_style) for text in closing]
    doc.build(story)
    return path


def build_electricity() -> Path:
    return _build(
        "TESTDATA_electricity_bill.pdf",
        "Test Fixture: Electricity Consumption Record",
        [
            "Utility: Example State Power Distribution (Test) Ltd<br/>"
            "Consumer number: TEST-HT2-0000000 | Tariff: HT-2 (test)",
            "Billing period: 01-01-2026 to 31-03-2026",
        ],
        [
            ["Meter field", "Value"],
            ["Opening reading", "1,250,000"],
            ["Closing reading", "1,500,000"],
            ["Multiplying factor", "1"],
            ["Billed demand", "850 kVA"],
            ["Active Energy Consumption: 250,000 kWh", "Test amount INR 0.00"],
        ],
        ["All identifiers and amounts are placeholders. No commercial transaction is represented."],
    )


def build_fuel() -> Path:
    return _build(
        "TESTDATA_fuel_record.pdf",
        "Test Fixture: Fuel Consumption Record",
        [
            "Supplier: Example Petroleum Traders (Test)<br/>"
            "Reference: TEST/2026/0000 | Date: 31-03-2026",
            "Line item description: Furnace Oil (industrial grade, test item)",
        ],
        [
            ["Description", "Quantity"],
            ["Furnace Oil (test)", "12,500 litres of Furnace Oil"],
            ["Rate", "INR 0.00 per litre (placeholder)"],
            ["Taxable value", "INR 0.00"],
        ],
        ["This is not a tax invoice. Amounts and identifiers are placeholders."],
    )


def build_precursor() -> Path:
    return _build(
        "TESTDATA_precursor_declaration.pdf",
        "Test Fixture: Precursor Material Declaration",
        [
            "Supplier: Example Wire Products (Test) Ltd<br/>"
            "Declaration: TEST/SEE/2026/0000 | Date: 05-04-2026",
        ],
        [
            ["Material field", "Value"],
            ["Material", "Steel Wire Rod (test)"],
            ["Steel Wire Rod supplied 520 tonnes", "CN 7228 30"],
            ["Specific embedded emissions", "1.85 tCO2e per tonne (placeholder)"],
            ["Supplier verification status", "Self-declared test value"],
        ],
        ["This declaration is a test fixture. The embedded-emissions figure is illustrative."],
    )


def build_production() -> Path:
    return _build(
        "TESTDATA_production_log.pdf",
        "Test Fixture: Quarterly Output Log",
        [
            "Product family: Steel fasteners (bolts, nuts, screws, washers) - test items",
            "Net Production Output: 500 tonnes",
        ],
        [
            ["Product group", "Output (tonnes)"],
            ["Bolts", "210"],
            ["Nuts", "140"],
            ["Screws", "100"],
            ["Washers", "50"],
            ["Total facility production: 625 tonnes", "All groups combined, test value"],
        ],
        ["Prepared by: Test Operator | Reviewed by: Test Reviewer (roles only, no personal data)"],
    )


def main() -> None:
    for builder in (build_electricity, build_fuel, build_precursor, build_production):
        print(builder())


if __name__ == "__main__":
    main()
