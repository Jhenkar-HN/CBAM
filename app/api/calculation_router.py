import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AuditTrail, CalculationResult, ReportingPeriod
from app.modules.calculation.engine import calculate_product_see
from app.schemas.calculation import (
    DeterministicCalculationRequest,
    DeterministicCalculationResult,
)

router = APIRouter(prefix="/calculations", tags=["Deterministic Calculation Core"])


@router.post("/calculate", response_model=DeterministicCalculationResult, status_code=status.HTTP_200_OK)
def run_calculation(
    request: DeterministicCalculationRequest,
    save_to_db: bool = True,
    db: Session = Depends(get_db),
):
    """
    Executes 100% deterministic carbon calculation followed by vectorized Monte Carlo uncertainty simulation.
    Preserves audit integrity and freezes input snapshots into the database.
    """
    try:
        result = calculate_product_see(request, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation engine error: {str(e)}")

    if save_to_db:
        period = db.query(ReportingPeriod).filter_by(id=request.reporting_period_id).first()
        if period:
            calc_record = CalculationResult(
                reporting_period_id=request.reporting_period_id,
                scope1_direct_tco2=result.allocated_scope1_direct_tco2,
                scope2_indirect_tco2=result.allocated_scope2_indirect_tco2,
                precursor_emissions_tco2=result.precursor_emissions_tco2,
                total_embedded_emissions_tco2=result.total_embedded_emissions_tco2,
                specific_embedded_emissions_see=result.specific_embedded_emissions_see,
                see_unit=result.see_unit,
                includes_indirect=result.includes_indirect_delta_cn,
                uncertainty_low_see=result.uncertainty_low_see,
                uncertainty_high_see=result.uncertainty_high_see,
                confidence_interval_pct=result.confidence_interval_pct,
                formula_applied=result.formula_latex,
                input_snapshot_json=json.dumps(result.input_snapshot),
                status="Calculated",
            )
            db.add(calc_record)

            # Record audit trail
            audit = AuditTrail(
                reporting_period_id=request.reporting_period_id,
                action="CALCULATION_EXECUTED",
                performed_by="Deterministic Engine",
                details_json=json.dumps({
                    "see": result.specific_embedded_emissions_see,
                    "target_cn": result.target_cn_code,
                    "alpha_p": result.allocation_factor_alpha,
                    "data_quality": result.data_quality_rating.value,
                }),
            )
            db.add(audit)
            db.commit()

    return result


@router.get("/period/{reporting_period_id}/latest")
def get_latest_calculation(
    reporting_period_id: int,
    db: Session = Depends(get_db),
):
    """Retrieves the most recent calculation record for a reporting period."""
    calc = (
        db.query(CalculationResult)
        .filter_by(reporting_period_id=reporting_period_id)
        .order_by(CalculationResult.id.desc())
        .first()
    )
    if not calc:
        raise HTTPException(
            status_code=404,
            detail=f"No calculation record found for reporting period {reporting_period_id}",
        )
    return calc
