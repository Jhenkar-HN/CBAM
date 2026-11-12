from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db.models import DocumentRecord, ExtractedFieldAudit
from app.modules.document_ai.extractor import run_document_ai_extraction
from app.schemas.document import (
    DocumentExtractionResult,
    DocumentRecordRead,
    ExtractedFieldAuditRead,
    HumanOverrideRequest,
)

router = APIRouter(prefix="/documents", tags=["Document AI & Evidence Ledger"])


@router.post("/upload", response_model=DocumentExtractionResult, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    1. Ingests multi-format factory records (PDF, PNG, JPG, CSV, XLSX).
    2. Computes immutable SHA-256 cryptographic digest.
    3. Runs schema-constrained Document AI extraction with verbatim evidence snippets.
    4. Persists document record and audit ledger entries.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extraction_result = run_document_ai_extraction(contents, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document parsing error: {str(e)}")

    # Secure local file persistence using hash
    safe_ext = Path(file.filename).suffix
    save_path = settings.UPLOAD_DIR / f"{extraction_result.document_hash}{safe_ext}"
    if not save_path.exists():
        save_path.write_bytes(contents)

    # Save or update document metadata record
    doc_record = db.query(DocumentRecord).filter_by(document_hash=extraction_result.document_hash).first()
    if not doc_record:
        doc_record = DocumentRecord(
            document_hash=extraction_result.document_hash,
            filename=file.filename,
            workspace_id=workspace_id,
            page_count=extraction_result.page_count,
            file_size_bytes=len(contents)
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

    # Save extracted field candidates to audit ledger if not already stored
    existing_fields = {
        f.field_name: f for f in db.query(ExtractedFieldAudit).filter_by(document_hash=extraction_result.document_hash).all()
    }

    for candidate in extraction_result.extracted_fields:
        if candidate.field_name not in existing_fields:
            audit_entry = ExtractedFieldAudit(
                document_hash=extraction_result.document_hash,
                field_name=candidate.field_name,
                field_category=candidate.field_category or "scope1_fuel",
                raw_extracted_value=str(candidate.extracted_value),
                raw_unit=candidate.unit,
                confidence_score=candidate.confidence_score,
                evidence_page=candidate.evidence_page,
                evidence_snippet=candidate.evidence_snippet,
                effective_value=str(candidate.extracted_value),
                effective_unit=candidate.unit,
                was_overridden=False
            )
            db.add(audit_entry)

    db.commit()
    return extraction_result


@router.post("/override")
def override_field_value(
    request: HumanOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Human-in-the-loop override endpoint:
    Logs user corrections while preserving the raw machine extraction for third-party verifier audits.
    """
    audit_entry = db.query(ExtractedFieldAudit).filter_by(
        document_hash=request.document_hash,
        field_name=request.field_name
    ).first()

    if not audit_entry:
        raise HTTPException(
            status_code=404,
            detail=f"Extracted field '{request.field_name}' not found for document {request.document_hash[:8]}..."
        )

    # Log human correction while keeping raw extraction intact
    audit_entry.user_override_value = str(request.override_value)
    audit_entry.user_override_unit = request.override_unit or audit_entry.raw_unit
    audit_entry.effective_value = str(request.override_value)
    audit_entry.effective_unit = request.override_unit or audit_entry.raw_unit
    audit_entry.was_overridden = True
    audit_entry.modified_by_user_id = request.user_id
    audit_entry.override_reason = request.override_reason

    db.commit()

    return {
        "status": "success",
        "message": f"Field '{request.field_name}' successfully updated.",
        "field_name": request.field_name,
        "raw_value": audit_entry.raw_extracted_value,
        "effective_value": audit_entry.effective_value,
        "effective_unit": audit_entry.effective_unit,
        "was_overridden": True,
        "modified_by": audit_entry.modified_by_user_id,
        "override_reason": audit_entry.override_reason,
    }


@router.get("/{document_hash}/fields", response_model=List[ExtractedFieldAuditRead])
def get_document_fields(
    document_hash: str,
    db: Session = Depends(get_db)
):
    """Returns all audit ledger fields extracted for a given document."""
    fields = db.query(ExtractedFieldAudit).filter_by(document_hash=document_hash).all()
    if not fields:
        raise HTTPException(status_code=404, detail="No extracted fields found for this document hash.")
    return fields


@router.get("/workspace/{workspace_id}", response_model=List[DocumentRecordRead])
def list_workspace_documents(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """Lists all files ingested in a workspace."""
    docs = db.query(DocumentRecord).filter_by(workspace_id=workspace_id).all()
    return docs
