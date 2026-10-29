"""Physical unit conversion and normalization service for deterministic carbon accounting."""

import re
from typing import Dict

# Normalization alias mappings (lowercase)
MASS_CONVERSIONS_TO_TONNES: Dict[str, float] = {
    "tonne": 1.0,
    "tonnes": 1.0,
    "metric ton": 1.0,
    "metric tons": 1.0,
    "t": 1.0,
    "mt": 1.0,
    "kg": 0.001,
    "kilogram": 0.001,
    "kilograms": 0.001,
    "g": 1e-6,
    "gram": 1e-6,
    "grams": 1e-6,
    "lb": 0.00045359237,
    "lbs": 0.00045359237,
    "pound": 0.00045359237,
    "pounds": 0.00045359237,
    "quintal": 0.1,
    "quintals": 0.1,
}

ELECTRICITY_CONVERSIONS_TO_MWH: Dict[str, float] = {
    "mwh": 1.0,
    "megawatt-hour": 1.0,
    "megawatt-hours": 1.0,
    "kwh": 0.001,
    "kilowatt-hour": 0.001,
    "kilowatt-hours": 0.001,
    "units": 0.001,
    "unit": 0.001,
    "gwh": 1000.0,
    "gigawatt-hour": 1000.0,
    "gigawatt-hours": 1000.0,
    "wh": 1e-6,
    "watt-hour": 1e-6,
    "watt-hours": 1e-6,
}

ENERGY_CONVERSIONS_TO_GJ: Dict[str, float] = {
    "gj": 1.0,
    "gigajoule": 1.0,
    "gigajoules": 1.0,
    "mj": 0.001,
    "megajoule": 0.001,
    "megajoules": 0.001,
    "tj": 1000.0,
    "terajoule": 1000.0,
    "terajoules": 1000.0,
    "kwh": 0.0036,
    "mwh": 3.6,
    "mmbtu": 1.05505585,
    "btu": 1.05505585e-6,
    "kcal": 4.184e-6,
    "gcal": 4.184,
}

VOLUME_CONVERSIONS_TO_LITRES: Dict[str, float] = {
    "litre": 1.0,
    "litres": 1.0,
    "liter": 1.0,
    "liters": 1.0,
    "l": 1.0,
    "m3": 1000.0,
    "nm3": 1000.0,
    "cubic meter": 1000.0,
    "cubic meters": 1000.0,
    "cubic metre": 1000.0,
    "cubic metres": 1000.0,
    "kl": 1000.0,
    "kilolitre": 1000.0,
    "kilolitres": 1000.0,
    "gal": 3.78541,
    "gallon": 3.78541,
    "gallons": 3.78541,
    "bbl": 158.987,
    "barrel": 158.987,
    "barrels": 158.987,
}


def clean_unit(unit_str: str) -> str:
    """Cleans and standardizes raw unit string."""
    if not unit_str:
        return ""
    # Strip spaces, special punctuation, and lowercase
    u = unit_str.strip().lower()
    u = re.sub(r'[\/\\_\-\.]', '', u)
    # Common replacements
    if u in ["tons", "ton", "tonnes", "tonne", "mt", "t"]:
        return "tonne"
    if u in ["kwh", "units", "unit"]:
        return "kwh"
    if u in ["mwh"]:
        return "mwh"
    if u in ["litre", "litres", "liter", "liters", "l"]:
        return "litre"
    if u in ["m3", "nm3"]:
        return "m3"
    return u


def to_metric_tonnes(quantity: float, unit: str) -> float:
    """Converts a mass quantity to standard metric tonnes."""
    if quantity < 0:
        raise ValueError(f"Quantity cannot be negative: {quantity}")
    u = unit.strip().lower()
    factor = MASS_CONVERSIONS_TO_TONNES.get(u)
    if factor is None:
        # Try cleaned unit
        clean_u = clean_unit(u)
        factor = MASS_CONVERSIONS_TO_TONNES.get(clean_u)
    if factor is None:
        raise ValueError(f"Unsupported mass unit: '{unit}'. Expected one of: {list(MASS_CONVERSIONS_TO_TONNES.keys())}")
    return quantity * factor


def to_megawatt_hours(quantity: float, unit: str) -> float:
    """Converts an electrical energy quantity to Megawatt-hours (MWh)."""
    if quantity < 0:
        raise ValueError(f"Electrical consumption cannot be negative: {quantity}")
    u = unit.strip().lower()
    factor = ELECTRICITY_CONVERSIONS_TO_MWH.get(u)
    if factor is None:
        clean_u = clean_unit(u)
        factor = ELECTRICITY_CONVERSIONS_TO_MWH.get(clean_u)
    if factor is None:
        raise ValueError(f"Unsupported electricity unit: '{unit}'. Expected one of: {list(ELECTRICITY_CONVERSIONS_TO_MWH.keys())}")
    return quantity * factor


def to_energy_gigajoules(quantity: float, unit: str, ncv_gj_per_unit: float = None) -> float:
    """
    Converts fuel consumption to energy content in Gigajoules (GJ).
    If unit is an energy unit (GJ, MJ, TJ, MMBTU), converts directly.
    If unit is a physical unit (litres, kg, m3, tonnes), multiplies by ncv_gj_per_unit.
    """
    if quantity < 0:
        raise ValueError(f"Fuel quantity cannot be negative: {quantity}")
    u = unit.strip().lower()

    # Direct energy unit conversion
    if u in ENERGY_CONVERSIONS_TO_GJ:
        return quantity * ENERGY_CONVERSIONS_TO_GJ[u]

    # Physical fuel quantity: requires NCV
    if ncv_gj_per_unit is None or ncv_gj_per_unit <= 0:
        raise ValueError(f"Net Calorific Value (NCV) is required to convert physical unit '{unit}' to Gigajoules.")

    return quantity * ncv_gj_per_unit
