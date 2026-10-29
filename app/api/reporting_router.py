"""FastAPI router for Regulatory RAG and Auditable ReportLab PDF/CSV generation."""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse
import io

from app.modules.rag.assistant import answer_regulatory_query
from app.modules.reporting.csv_generator import generate_passport_csv
from app.modules.reporting.pdf_generator import generate_passport_pdf
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse

router = APIRouter(tags=["Regulatory RAG & Auditable Reporting"])


@router.post("/rag/query", response_model=RAGQueryResponse, status_code=status.HTTP_200_OK)
def query_regulatory_rag(request: RAGQueryRequest):
    """
    Queries the official European Commission CBAM regulatory corpus.
    Returns source-grounded guidance with exact section citations and hallucination guards.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        response = answer_regulatory_query(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search error: {str(e)}")


@router.post("/passport/download-pdf")
def download_passport_pdf(passport_data: Dict[str, Any]):
    """
    Generates and downloads the official CBAM Emissions Passport in PDF format.
    Includes cryptographic SHA-256 evidence links, mathematical breakdown, and legal disclaimers.
    """
    try:
        pdf_bytes = generate_passport_pdf(passport_data)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        cn_code = passport_data.get("workspace", {}).get("cn_code", "7318").replace(" ", "_")
        filename = f"CBAM_Passport_{cn_code}_{timestamp}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")


@router.post("/passport/download-csv")
def download_passport_csv(passport_data: Dict[str, Any]):
    """
    Generates and downloads the machine-readable CBAM Audit Evidence Ledger in CSV format.
    """
    try:
        csv_text = generate_passport_csv(passport_data)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        cn_code = passport_data.get("workspace", {}).get("cn_code", "7318").replace(" ", "_")
        filename = f"CBAM_Audit_Ledger_{cn_code}_{timestamp}.csv"

        return Response(
            content=csv_text.encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV generation error: {str(e)}")
