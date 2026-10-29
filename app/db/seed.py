"""Initial database seeder for CBAM CN codes and standard emission factors."""

from app.db.database import SessionLocal, init_db
from app.db.models import CBAMDefaultValues, CNCodeRegistry


def seed_database():
    init_db()
    db = SessionLocal()
    try:
        # 1. Seed Pilot CN Codes (Steel Fasteners & Precursors)
        cn_codes = [
            CNCodeRegistry(
                cn_code="7318 15 82",
                description="Other screws and bolts, whether or not with their nuts or washers, of steel, without heads or with cold formed heads",
                sector="Iron and Steel",
                includes_indirect_emissions=True,  # delta_CN = 1
                requires_precursors=True,
                default_unit="tonne",
                notes="Primary pilot CN code for Indian cold-forging fastener manufacturers."
            ),
            CNCodeRegistry(
                cn_code="7318 15 95",
                description="Other screws and bolts, of steel, with heads, tensile strength < 800 MPa",
                sector="Iron and Steel",
                includes_indirect_emissions=True,
                requires_precursors=True,
                default_unit="tonne",
                notes="Pilot CN code for standard mild steel bolts."
            ),
            CNCodeRegistry(
                cn_code="7318 16 00",
                description="Nuts, of steel",
                sector="Iron and Steel",
                includes_indirect_emissions=True,
                requires_precursors=True,
                default_unit="tonne",
                notes="Hex nuts and locking nuts."
            ),
            CNCodeRegistry(
                cn_code="7228 30",
                description="Precursor: Other bars and rods of other alloy steel; wire rod",
                sector="Iron and Steel (Precursor)",
                includes_indirect_emissions=True,
                requires_precursors=False,
                default_unit="tonne",
                notes="Raw material wire rod used in cold heading fasteners."
            ),
        ]

        for item in cn_codes:
            existing = db.query(CNCodeRegistry).filter_by(cn_code=item.cn_code).first()
            if not existing:
                db.add(item)

        # 2. Seed Standard Default Emission & Calorific Factors
        default_factors = [
            # Scope 1 - Fuels
            CBAMDefaultValues(
                category="fuel",
                item_name="Furnace Oil",
                unit="litre",
                ncv_value=0.0402,  # GJ / litre
                ncv_unit="GJ/litre",
                ef_value=0.0774,  # tCO2 / GJ
                ef_unit="tCO2/GJ",
                oxidation_factor=1.0,
                geographic_scope="India / Global",
                source_reference="IPCC 2006 Guidelines for National GHG Inventories, Vol 2"
            ),
            CBAMDefaultValues(
                category="fuel",
                item_name="Diesel (HSD)",
                unit="litre",
                ncv_value=0.0357,  # GJ / litre
                ncv_unit="GJ/litre",
                ef_value=0.0741,  # tCO2 / GJ
                ef_unit="tCO2/GJ",
                oxidation_factor=1.0,
                geographic_scope="India / Global",
                source_reference="IPCC 2006 Guidelines, Vol 2 Energy"
            ),
            CBAMDefaultValues(
                category="fuel",
                item_name="Natural Gas",
                unit="Nm3",
                ncv_value=0.0385,  # GJ / Nm3
                ncv_unit="GJ/Nm3",
                ef_value=0.0561,  # tCO2 / GJ
                ef_unit="tCO2/GJ",
                oxidation_factor=1.0,
                geographic_scope="India / Global",
                source_reference="IPCC 2006 Guidelines, Vol 2 Energy"
            ),
            CBAMDefaultValues(
                category="fuel",
                item_name="LPG",
                unit="kg",
                ncv_value=0.0461,  # GJ / kg
                ncv_unit="GJ/kg",
                ef_value=0.0631,  # tCO2 / GJ
                ef_unit="tCO2/GJ",
                oxidation_factor=1.0,
                geographic_scope="India / Global",
                source_reference="IPCC 2006 Guidelines, Vol 2 Energy"
            ),

            # Scope 2 - Electricity
            CBAMDefaultValues(
                category="electricity",
                item_name="Indian National Grid (CEA v19 Baseline)",
                unit="kWh",
                ncv_value=None,
                ncv_unit=None,
                ef_value=0.716,  # tCO2 / MWh (0.000716 tCO2/kWh)
                ef_unit="tCO2/MWh",
                oxidation_factor=1.0,
                geographic_scope="India (National Average)",
                source_reference="Central Electricity Authority (CEA) CO2 Baseline Database v19 (2024)"
            ),
            CBAMDefaultValues(
                category="electricity",
                item_name="EU CBAM Default - India Iron & Steel Grid",
                unit="kWh",
                ncv_value=None,
                ncv_unit=None,
                ef_value=0.820,  # tCO2 / MWh
                ef_unit="tCO2/MWh",
                oxidation_factor=1.0,
                geographic_scope="India",
                source_reference="European Commission Guidance on Default Values for CBAM (2024)"
            ),

            # Precursor - Steel Raw Materials
            CBAMDefaultValues(
                category="precursor",
                item_name="Steel Wire Rod (DRI-EAF Route - Indian Benchmark)",
                unit="tonne",
                ncv_value=None,
                ncv_unit=None,
                ef_value=1.85,  # tCO2 / tonne of steel
                ef_unit="tCO2/t",
                oxidation_factor=1.0,
                geographic_scope="India",
                source_reference="Indian Steel Sector Decarbonisation Roadmap / Ministry of Steel"
            ),
            CBAMDefaultValues(
                category="precursor",
                item_name="Steel Wire Rod (BF-BOF Primary Route)",
                unit="tonne",
                ncv_value=None,
                ncv_unit=None,
                ef_value=2.15,  # tCO2 / tonne of steel
                ef_unit="tCO2/t",
                oxidation_factor=1.0,
                geographic_scope="India / Global",
                source_reference="World Steel Association 2023 Sustainability Indicators"
            ),
            CBAMDefaultValues(
                category="precursor",
                item_name="EU CBAM Default - Alloy Steel Wire Rod (India)",
                unit="tonne",
                ncv_value=None,
                ncv_unit=None,
                ef_value=2.24,  # tCO2 / tonne of steel
                ef_unit="tCO2/t",
                oxidation_factor=1.0,
                geographic_scope="India (EU Default Fallback)",
                source_reference="European Commission Official Default Values for Transitional Period"
            ),
        ]

        for item in default_factors:
            existing = db.query(CBAMDefaultValues).filter_by(
                category=item.category,
                item_name=item.item_name
            ).first()
            if not existing:
                db.add(item)

        db.commit()
        print("Database initialized and successfully seeded with pilot CN codes and default factors.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
