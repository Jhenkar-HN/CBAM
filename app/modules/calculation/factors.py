"""Reference factor lookups backed by the seeded CBAM reference tables.

The database is the single source of truth for CN classification and default
emission factors. Nothing in this module invents or duplicates factor values.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import CBAMDefaultValues, CNCodeRegistry


def _serialize(row: CBAMDefaultValues) -> Dict[str, Any]:
    return {
        "id": row.id,
        "category": row.category,
        "item_name": row.item_name,
        "unit": row.unit,
        "ncv_value": row.ncv_value,
        "ncv_unit": row.ncv_unit,
        "ef_value": row.ef_value,
        "ef_unit": row.ef_unit,
        "oxidation_factor": row.oxidation_factor,
        "geographic_scope": row.geographic_scope,
        "source_reference": row.source_reference,
        "cn_code": row.cn_code,
        "markup_pct": row.markup_pct,
    }


def list_factors(db: Session) -> Dict[str, List[Dict[str, Any]]]:
    """Returns every active reference factor grouped by category."""
    rows = (
        db.query(CBAMDefaultValues)
        .filter(CBAMDefaultValues.is_active.is_(True))
        .order_by(CBAMDefaultValues.category, CBAMDefaultValues.item_name)
        .all()
    )
    grouped: Dict[str, List[Dict[str, Any]]] = {"fuel": [], "electricity": [], "precursor": []}
    for row in rows:
        if row.category in grouped:
            grouped[row.category].append(_serialize(row))
    return grouped


def list_cn_codes(db: Session) -> List[Dict[str, Any]]:
    rows = db.query(CNCodeRegistry).order_by(CNCodeRegistry.cn_code).all()
    return [
        {
            "cn_code": row.cn_code,
            "description": row.description,
            "sector": row.sector,
            "includes_indirect_emissions": bool(row.includes_indirect_emissions),
            "requires_precursors": bool(row.requires_precursors),
            "default_unit": row.default_unit,
            "notes": row.notes,
        }
        for row in rows
    ]


def find_cn_code(db: Session, cn_code: str) -> Optional[CNCodeRegistry]:
    if not cn_code:
        return None
    return db.query(CNCodeRegistry).filter_by(cn_code=cn_code).first()


def find_factor(
    db: Session,
    category: str,
    item_name: Optional[str] = None,
    cn_code: Optional[str] = None,
) -> Optional[CBAMDefaultValues]:
    """Finds a factor by exact name, then by containment, then by CN code."""
    query = db.query(CBAMDefaultValues).filter(
        CBAMDefaultValues.category == category,
        CBAMDefaultValues.is_active.is_(True),
    )
    rows = query.order_by(CBAMDefaultValues.item_name).all()
    if not rows:
        return None

    if cn_code:
        for row in rows:
            if row.cn_code and row.cn_code.replace(" ", "") == cn_code.replace(" ", ""):
                return row

    if item_name:
        needle = item_name.strip().lower()
        for row in rows:
            if row.item_name.strip().lower() == needle:
                return row
        for row in rows:
            haystack = row.item_name.strip().lower()
            if needle and (needle in haystack or haystack in needle):
                return row

    return None


def resolve_fuel_factors(db: Session, fuel_name: str) -> Optional[CBAMDefaultValues]:
    return find_factor(db, "fuel", item_name=fuel_name)


def resolve_electricity_factor(db: Session, source_name: Optional[str]) -> Optional[CBAMDefaultValues]:
    return find_factor(db, "electricity", item_name=source_name)


def resolve_precursor_default(db: Session, cn_code: Optional[str]) -> Optional[CBAMDefaultValues]:
    if not cn_code:
        return None
    return find_factor(db, "precursor", cn_code=cn_code)
