"""Script to generate 10 diverse, realistic synthetic documents for steel fastener CBAM compliance."""

import os
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

OUTPUT_DIR = Path("C:/Users/haris/CBAM/data/sample_docs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_pdf(filename: str, story: list):
    filepath = OUTPUT_DIR / filename
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    doc.build(story)
    print(f"Generated PDF: {filepath}")

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "InvTitle",
    parent=styles["Heading1"],
    fontSize=14,
    leading=18,
    textColor=colors.HexColor("#1e293b"),
)
body_style = ParagraphStyle(
    "InvBody",
    parent=styles["Normal"],
    fontSize=8.5,
    leading=12,
    textColor=colors.HexColor("#334155"),
)
bold_style = ParagraphStyle(
    "InvBold",
    parent=body_style,
    fontName="Helvetica-Bold",
)
header_cell = ParagraphStyle(
    "HeaderCell",
    parent=body_style,
    fontName="Helvetica-Bold",
    textColor=colors.HexColor("#0f172a"),
)

# -------------------------------------------------------------
# 1. DHBVN HT Industrial Electricity Bill (PDF)
# -------------------------------------------------------------
def make_doc_1():
    story = [
        Paragraph("DAKSHIN HARYANA BIJLI VITRAN NIGAM (DHBVN)", title_style),
        Paragraph("HT Industrial Electricity Consumption Invoice & Demand Note", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Consumer Name:</b>", body_style), Paragraph("Apex Fasteners Pvt Ltd (Unit-1 Cold Forging)", body_style),
         Paragraph("<b>Bill Month:</b>", body_style), Paragraph("October 2026", body_style)],
        [Paragraph("<b>Connection No:</b>", body_style), Paragraph("HT-FDB-58-99410", body_style),
         Paragraph("<b>Supply Voltage:</b>", body_style), Paragraph("11 kV Industrial Feeder", body_style)],
        [Paragraph("<b>Meter Serial:</b>", body_style), Paragraph("SEC-LNT-88921", body_style),
         Paragraph("<b>Tariff Category:</b>", body_style), Paragraph("HT Industry (Continuous)", body_style)],
    ]
    t_meta = Table(meta, colWidths=[110, 240, 90, 100])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>METER READINGS & RECORDED ENERGY:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Parameter", header_cell), Paragraph("Previous Reading", header_cell), Paragraph("Current Reading", header_cell), Paragraph("Multiplying Factor (MF)", header_cell), Paragraph("Billed Energy", header_cell)],
        [Paragraph("Active Energy (kWh)", body_style), Paragraph("1,450,200", body_style), Paragraph("1,700,200", body_style), Paragraph("1.0", body_style), Paragraph("<b>250,000 kWh</b>", bold_style)],
        [Paragraph("Reactive Energy (kVARh)", body_style), Paragraph("410,000", body_style), Paragraph("475,000", body_style), Paragraph("1.0", body_style), Paragraph("65,000 kVARh", body_style)],
        [Paragraph("Average Power Factor", body_style), Paragraph("0.96 Lagging", body_style), Paragraph("—", body_style), Paragraph("—", body_style), Paragraph("0.96 PF", body_style)],
    ]
    t_read = Table(table_data, colWidths=[160, 95, 95, 100, 90])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Note: Total Active Energy Consumption recorded for billing period is <b>250,000 kWh</b>. Verified against Grid Substation metering.", body_style))
    create_pdf("01_DHBVN_Electricity_Bill_Oct2026.pdf", story)

# -------------------------------------------------------------
# 2. PSPCL Punjab Utility Bill (Alternative Grid Scope 2) (PDF)
# -------------------------------------------------------------
def make_doc_2():
    story = [
        Paragraph("PUNJAB STATE POWER CORPORATION LIMITED (PSPCL)", title_style),
        Paragraph("Large Supply Industrial Billing Statement - Mandi Gobindgarh Circle", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0891b2"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Consumer:</b>", body_style), Paragraph("Apex Fasteners Ltd - Unit 2 Cold Heading Division", body_style),
         Paragraph("<b>Bill Cycle:</b>", body_style), Paragraph("September 2026", body_style)],
        [Paragraph("<b>Consumer A/C:</b>", body_style), Paragraph("3002998811", body_style),
         Paragraph("<b>Substation:</b>", body_style), Paragraph("66kV Mandi Gobindgarh Focal Point", body_style)],
    ]
    t_meta = Table(meta, colWidths=[90, 260, 80, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>ENERGY CONSUMPTION SUMMARY:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Category", header_cell), Paragraph("Total kWh Units", header_cell), Paragraph("Total MWh Equivalent", header_cell), Paragraph("Net Energy Charges (INR)", header_cell)],
        [Paragraph("Industrial Power (Peak & Off-Peak)", body_style), Paragraph("185,000 kWh", bold_style), Paragraph("185.0 MWh", body_style), Paragraph("Rs. 1,295,000.00", body_style)],
        [Paragraph("Auxiliary Plant Lighting", body_style), Paragraph("15,000 kWh", body_style), Paragraph("15.0 MWh", body_style), Paragraph("Rs. 105,000.00", body_style)],
        [Paragraph("<b>Combined Facility Power</b>", bold_style), Paragraph("<b>200,000 kWh</b>", bold_style), Paragraph("<b>200.0 MWh</b>", bold_style), Paragraph("<b>Rs. 1,400,000.00</b>", bold_style)],
    ]
    t_read = Table(table_data, colWidths=[180, 110, 110, 140])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ccfbf1")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e6fffa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Total recorded active electricity consumption is <b>200,000 kWh</b> for the annealing and wire drawing shop.", body_style))
    create_pdf("02_PSPCL_Industrial_Electricity_Bill.pdf", story)

# -------------------------------------------------------------
# 3. IOCL Bulk Furnace Oil Delivery Challan (PDF)
# -------------------------------------------------------------
def make_doc_3():
    story = [
        Paragraph("INDIAN OIL CORPORATION LIMITED (IOCL)", title_style),
        Paragraph("Bulk Industrial Fuel Delivery Challan & Commercial Tax Invoice", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#ea580c"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Invoice No:</b>", body_style), Paragraph("IOCL/PANIPAT/FO/2026/8942", body_style),
         Paragraph("<b>Date:</b>", body_style), Paragraph("14-October-2026", body_style)],
        [Paragraph("<b>Consignee:</b>", body_style), Paragraph("Apex Fasteners Pvt Ltd (Annealing Furnace Yard)", body_style),
         Paragraph("<b>Tanker Lorry No:</b>", body_style), Paragraph("HR-38-AF-4412", body_style)],
        [Paragraph("<b>Dispatch Terminal:</b>", body_style), Paragraph("Panipat Refinery Marketing Terminal", body_style),
         Paragraph("<b>Fuel Grade:</b>", body_style), Paragraph("Furnace Oil (FO 180 cSt)", body_style)],
    ]
    t_meta = Table(meta, colWidths=[100, 240, 90, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fed7aa")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>PRODUCT DISPATCH PARTICULARS:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Description of Goods", header_cell), Paragraph("Density @ 15 C", header_cell), Paragraph("Dispatched Quantity", header_cell), Paragraph("Gross Calorific Value", header_cell), Paragraph("Net Delivered", header_cell)],
        [Paragraph("Industrial Furnace Oil (IS 1593:2018)", body_style), Paragraph("0.942 kg/L", body_style), Paragraph("15,000 litres", bold_style), Paragraph("10,200 kcal/kg", body_style), Paragraph("<b>15,000 litres of furnace oil</b>", bold_style)],
    ]
    t_read = Table(table_data, colWidths=[170, 80, 90, 100, 100])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ffedd5")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fed7aa")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Certified that Furnace Oil Dispatched: <b>15,000 litres</b> to customer underground storage tank #2 for heat-treatment furnaces.", body_style))
    create_pdf("03_IOCL_Furnace_Oil_Challan.pdf", story)

# -------------------------------------------------------------
# 4. Bharat Petroleum High Speed Diesel (HSD) Slip (PDF)
# -------------------------------------------------------------
def make_doc_4():
    story = [
        Paragraph("BHARAT PETROLEUM CORPORATION LIMITED (BPCL)", title_style),
        Paragraph("High Speed Diesel (HSD) Supply Challan for Industrial Power DG Sets", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#16a34a"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Challan No:</b>", body_style), Paragraph("BPCL/HSD/FBD/2026/0411", body_style),
         Paragraph("<b>Date of Issue:</b>", body_style), Paragraph("22-October-2026", body_style)],
        [Paragraph("<b>Delivered To:</b>", body_style), Paragraph("Apex Fasteners Pvt Ltd - 500kVA DG Backup Station", body_style),
         Paragraph("<b>Vehicle No:</b>", body_style), Paragraph("DL-1M-AA-9022", body_style)],
    ]
    t_meta = Table(meta, colWidths=[90, 260, 80, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>FUEL SUPPLY SPECIFICATIONS:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Fuel Product", header_cell), Paragraph("Batch No", header_cell), Paragraph("Delivered Volume", header_cell), Paragraph("Application", header_cell)],
        [Paragraph("High Speed Diesel (BS-VI Automotive & Stationary)", body_style), Paragraph("HSD-26-B91", body_style), Paragraph("<b>4,500 litres of diesel</b>", bold_style), Paragraph("Standby DG Set Generator", body_style)],
    ]
    t_read = Table(table_data, colWidths=[200, 80, 120, 140])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Dispensed Total: <b>4,500 litres of diesel</b> into DG Day Tanks. Net Calorific Value: 0.0357 GJ/litre.", body_style))
    create_pdf("04_BPCL_Diesel_Supply_Challan.pdf", story)

# -------------------------------------------------------------
# 5. IGL Piped Natural Gas (PNG) Invoice (PDF)
# -------------------------------------------------------------
def make_doc_5():
    story = [
        Paragraph("INDRAPRASTHA GAS LIMITED (IGL)", title_style),
        Paragraph("Commercial & Industrial Piped Natural Gas (PNG) Metered Tax Invoice", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Customer Name:</b>", body_style), Paragraph("Apex Fasteners Pvt Ltd (Continuous Annealing Line)", body_style),
         Paragraph("<b>Billing Month:</b>", body_style), Paragraph("October 2026", body_style)],
        [Paragraph("<b>Customer ID:</b>", body_style), Paragraph("PNG-IND-771249", body_style),
         Paragraph("<b>Meter Model:</b>", body_style), Paragraph("Rotary Gas Meter RM-G65", body_style)],
    ]
    t_meta = Table(meta, colWidths=[100, 250, 80, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bae6fd")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>METER CONSUMPTION RECORD:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Gas Meter Category", header_cell), Paragraph("Initial SCM", header_cell), Paragraph("Final SCM", header_cell), Paragraph("Gross Volume", header_cell), Paragraph("Billed Consumption", header_cell)],
        [Paragraph("Industrial Piped Natural Gas", body_style), Paragraph("84,100", body_style), Paragraph("92,600", body_style), Paragraph("8,500 SCM", body_style), Paragraph("<b>8,500 m3 natural gas</b>", bold_style)],
    ]
    t_read = Table(table_data, colWidths=[160, 80, 80, 90, 130])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bae6fd")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Total recorded consumption is <b>8,500 m3 natural gas</b> for heat treatment furnaces.", body_style))
    create_pdf("05_IGL_Natural_Gas_Invoice.pdf", story)

# -------------------------------------------------------------
# 6. Jindal Steel Mill Test Certificate (MTC) - Actual Precursor (PDF)
# -------------------------------------------------------------
def make_doc_6():
    story = [
        Paragraph("JINDAL STEEL & POWER LIMITED (JSPL)", title_style),
        Paragraph("Inspection & Mill Test Certificate (EN 10204 3.1) - Alloy Steel Wire Rod", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4338ca"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Certificate No:</b>", body_style), Paragraph("JSPL/MTC/WR/2026/09912", body_style),
         Paragraph("<b>Date of Issue:</b>", body_style), Paragraph("08-October-2026", body_style)],
        [Paragraph("<b>Customer:</b>", body_style), Paragraph("Apex Fasteners Pvt Ltd (Cold Heading Plant)", body_style),
         Paragraph("<b>Purchase Order:</b>", body_style), Paragraph("PO-APX-WR-781", body_style)],
        [Paragraph("<b>Steel Grade:</b>", body_style), Paragraph("10B21 Boron Steel Cold Heading Quality", body_style),
         Paragraph("<b>Heat Number:</b>", body_style), Paragraph("HT-26-88194", body_style)],
        [Paragraph("<b>Product Form:</b>", body_style), Paragraph("Wire rod in irregularly wound coils (Dia 8.5 mm)", body_style),
         Paragraph("<b>EU CN Code:</b>", body_style), Paragraph("7228 30 (Alloy Wire Rod)", body_style)],
    ]
    t_meta = Table(meta, colWidths=[90, 250, 90, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eef2ff")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d2fe")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>CONSIGNMENT QUANTITY & CBAM EMISSIONS DECLARATION:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Item Specification", header_cell), Paragraph("Bundle Count", header_cell), Paragraph("Net Dispatched Mass", header_cell), Paragraph("Supplier Specific Embedded Emissions (SEE)", header_cell)],
        [Paragraph("Grade 10B21 CHQ Wire Rod 8.5mm", body_style), Paragraph("260 Coils", body_style), Paragraph("<b>520 tonnes</b>", bold_style), Paragraph("<b>1.85 tCO2/t</b> (DRI-EAF Route)", bold_style)],
    ]
    t_read = Table(table_data, colWidths=[170, 70, 100, 200])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d2fe")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Primary Material Data: Consigned Precursor Wire Rod: <b>520 tonnes</b> with actual Specific Embedded Emissions of <b>1.85 tCO2/t</b> verified by third-party mill auditor.", body_style))
    create_pdf("06_JSPL_Steel_Wire_Rod_Mill_Cert.pdf", story)

# -------------------------------------------------------------
# 7. Tata Steel Raw Material Delivery Challan (PDF)
# -------------------------------------------------------------
def make_doc_7():
    story = [
        Paragraph("TATA STEEL LIMITED - WIRE DIVISION", title_style),
        Paragraph("Commercial Dispatch Challan - High Carbon & Alloy Steel Wire Rods", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Challan Ref:</b>", body_style), Paragraph("TSL/TARAPUR/WR/2026/4102", body_style),
         Paragraph("<b>Despatch Date:</b>", body_style), Paragraph("18-October-2026", body_style)],
        [Paragraph("<b>Consignee:</b>", body_style), Paragraph("Apex Fasteners Pvt Ltd - Plot 42 Sector 58 Faridabad", body_style),
         Paragraph("<b>Carrier:</b>", body_style), Paragraph("Dedicated Trailer Fleet", body_style)],
    ]
    t_meta = Table(meta, colWidths=[90, 260, 80, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>CONSIGNMENT LINE ITEMS:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Material Description", header_cell), Paragraph("Coil Dia", header_cell), Paragraph("Heat Number", header_cell), Paragraph("Net Weight Supplied", header_cell)],
        [Paragraph("Alloy Steel Wire Rod Grade 4140/SCM435", body_style), Paragraph("10.0 mm", body_style), Paragraph("TSL-HT-90114", body_style), Paragraph("<b>310 tonnes</b>", bold_style)],
        [Paragraph("Mild Steel Cold Heading Wire Rod Grade 1018", body_style), Paragraph("6.5 mm", body_style), Paragraph("TSL-HT-90118", body_style), Paragraph("<b>190 tonnes</b>", bold_style)],
        [Paragraph("<b>Total Raw Material Precursor</b>", bold_style), Paragraph("—", body_style), Paragraph("—", body_style), Paragraph("<b>500 tonnes</b>", bold_style)],
    ]
    t_read = Table(table_data, colWidths=[200, 70, 100, 170])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Verified Weighment Slip Attached: Total Precursor Steel Quantity: <b>500 tonnes</b> received at plant gate.", body_style))
    create_pdf("07_Tata_Steel_Wire_Rod_Challan.pdf", story)

# -------------------------------------------------------------
# 8. Factory Weighbridge Summary & Production Output (PDF)
# -------------------------------------------------------------
def make_doc_8():
    story = [
        Paragraph("APEX FASTENERS PRIVATE LIMITED", title_style),
        Paragraph("Monthly Production Weighbridge Log & Warehouse Finished Goods Packing Slip", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=8),
        Spacer(1, 4),
    ]
    meta = [
        [Paragraph("<b>Facility:</b>", body_style), Paragraph("Apex Fasteners Unit 1 (Cold Forging & Thread Rolling)", body_style),
         Paragraph("<b>Period:</b>", body_style), Paragraph("1-Oct-2026 to 31-Oct-2026", body_style)],
        [Paragraph("<b>Weighbridge S/N:</b>", body_style), Paragraph("WB-FDB-60T-Calibrated", body_style),
         Paragraph("<b>Location:</b>", body_style), Paragraph("Faridabad, Haryana (IN FDB)", body_style)],
    ]
    t_meta = Table(meta, colWidths=[100, 250, 80, 110])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#5eead4")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>NET MANUFACTURING PRODUCTION SUMMARY:</b>", bold_style))
    story.append(Spacer(1, 4))
    
    table_data = [
        [Paragraph("Product Family / Line", header_cell), Paragraph("CN / HS Code", header_cell), Paragraph("Net Finished Weight", header_cell), Paragraph("Packing Units", header_cell)],
        [Paragraph("Hex Head Bolts & Screws (Grade 8.8 / 10.9)", body_style), Paragraph("7318 15 82", bold_style), Paragraph("<b>350 tonnes</b>", bold_style), Paragraph("7,000 corrugated boxes", body_style)],
        [Paragraph("Socket Head Cap Screws & Studs", body_style), Paragraph("7318 15 95", bold_style), Paragraph("<b>150 tonnes</b>", bold_style), Paragraph("3,000 corrugated boxes", body_style)],
        [Paragraph("<b>Target Finished Fasteners Net Output</b>", bold_style), Paragraph("<b>7318 Group</b>", bold_style), Paragraph("<b>500 tonnes</b>", bold_style), Paragraph("<b>10,000 boxes total</b>", bold_style)],
        [Paragraph("Non-covered Automotive Stamping Components", body_style), Paragraph("8708 29 90", body_style), Paragraph("125 tonnes", body_style), Paragraph("Shared facility output", body_style)],
        [Paragraph("<b>Total Plant Production (All Products)</b>", bold_style), Paragraph("All lines", body_style), Paragraph("<b>625 tonnes</b>", bold_style), Paragraph("Full facility throughput", bold_style)],
    ]
    t_read = Table(table_data, colWidths=[180, 90, 130, 140])
    t_read.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ccfbf1")),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#e6fffa")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#5eead4")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_read)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Verified Weighbridge Log: Net Production Output of Target Fasteners is <b>500 tonnes</b>; Total Facility Production Across All Products is <b>625 tonnes</b>.", body_style))
    create_pdf("08_Factory_Production_Weighbridge_Summary.pdf", story)

# -------------------------------------------------------------
# 9. Monthly Plant Energy & Multi-Product Log (CSV)
# -------------------------------------------------------------
def make_doc_9():
    filepath = OUTPUT_DIR / "09_Plant_Monthly_Energy_Log.csv"
    data = [
        {"Month": "October 2026", "Department": "Cold Heading Line 1", "Fuel_Type": "Furnace Oil", "Fuel_Quantity": "15,000 litres of furnace oil", "Electricity_Recorded": "250,000 kWh", "Raw_Precursor_In": "520 tonnes", "Net_Fasteners_Production": "500 tonnes", "Total_Plant_Output": "625 tonnes"},
        {"Month": "September 2026", "Department": "Cold Heading Line 1", "Fuel_Type": "Furnace Oil", "Fuel_Quantity": "14,200 litres of furnace oil", "Electricity_Recorded": "242,000 kWh", "Raw_Precursor_In": "495 tonnes", "Net_Fasteners_Production": "480 tonnes", "Total_Plant_Output": "600 tonnes"},
        {"Month": "August 2026", "Department": "Cold Heading Line 1", "Fuel_Type": "Furnace Oil", "Fuel_Quantity": "13,800 litres of furnace oil", "Electricity_Recorded": "235,000 kWh", "Raw_Precursor_In": "475 tonnes", "Net_Fasteners_Production": "460 tonnes", "Total_Plant_Output": "580 tonnes"},
    ]
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    print(f"Generated CSV: {filepath}")

# -------------------------------------------------------------
# 10. Precursor Inward & Supplier Mill Register (XLSX)
# -------------------------------------------------------------
def make_doc_10():
    filepath = OUTPUT_DIR / "10_Precursor_WireRod_Inward_Register.xlsx"
    data = [
        {"Inward_Date": "08-Oct-2026", "Supplier": "Jindal Steel & Power Ltd", "Challan_No": "JSPL/WR/8891", "Material_Grade": "Alloy Wire Rod 10B21", "Coil_Diameter_mm": 8.5, "Inward_Mass": "520 tonnes", "Supplier_Specific_Emissions": "1.85 tCO2/t", "Verified_Certificate": "Yes (3.1 MTC)"},
        {"Inward_Date": "18-Oct-2026", "Supplier": "Tata Steel Limited", "Challan_No": "TSL/4102", "Material_Grade": "Wire Rod Grade 4140", "Coil_Diameter_mm": 10.0, "Inward_Mass": "310 tonnes", "Supplier_Specific_Emissions": "1.92 tCO2/t", "Verified_Certificate": "Yes (3.1 MTC)"},
        {"Inward_Date": "25-Oct-2026", "Supplier": "Rashtriya Ispat Nigam Ltd (RINL)", "Challan_No": "RINL/0942", "Material_Grade": "Carbon Wire Rod 1018", "Coil_Diameter_mm": 6.5, "Inward_Mass": "190 tonnes", "Supplier_Specific_Emissions": "2.10 tCO2/t", "Verified_Certificate": "Yes (3.1 MTC)"},
    ]
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    print(f"Generated XLSX: {filepath}")

if __name__ == "__main__":
    make_doc_1()
    make_doc_2()
    make_doc_3()
    make_doc_4()
    make_doc_5()
    make_doc_6()
    make_doc_7()
    make_doc_8()
    make_doc_9()
    make_doc_10()
    print("All 10 synthetic documents successfully generated in data/sample_docs/")
