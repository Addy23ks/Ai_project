import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentResultResponse,
    ProcessingStep
)
from app.services.file_storage import storage_service
from app.services.pipeline import pipeline_orchestrator
from app.services.azure_ocr import azure_ocr_service
from app.services.transcription_model import transcription_service
from app.services.verification_model import verification_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/config-status")
def get_config_status():
    """Returns configuration status without revealing secrets."""
    return {
        "azure_ocr_configured": azure_ocr_service.is_configured,
        "model_a_configured": transcription_service.adapter.is_configured,
        "model_a_provider": settings.MODEL_A_PROVIDER,
        "model_a_model": settings.MODEL_A_DEPLOYMENT,
        "model_b_configured": verification_service.adapter.is_configured,
        "model_b_provider": settings.MODEL_B_PROVIDER,
        "model_b_model": settings.MODEL_B_DEPLOYMENT,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "max_document_pages": settings.MAX_DOCUMENT_PAGES,
        "pass_threshold": settings.PASS_THRESHOLD,
        "review_threshold": settings.REVIEW_THRESHOLD
    }


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Uploads and validates a scanned document file."""
    doc_id, detected_type, file_path, file_size = await storage_service.save_uploaded_file(file)

    # Register in pipeline tracker
    job = pipeline_orchestrator.register_job(
        document_id=doc_id,
        filename=file.filename or "uploaded_document",
        file_path=file_path
    )

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename or "uploaded_document",
        file_size=file_size,
        page_count=1,
        created_at=job.created_at,
        status=ProcessingStep.PENDING
    )


@router.post("/{document_id}/extract")
async def start_extraction(
    document_id: str,
    background_tasks: BackgroundTasks,
    wait: bool = Query(default=False)
):
    """Initiates the multi-step extraction and validation pipeline."""
    job = pipeline_orchestrator.get_job(document_id)
    if not job:
        raise HTTPException(status_code=404, detail="Document not found.")

    if job.status not in (ProcessingStep.PENDING, ProcessingStep.FAILED):
        return {
            "message": "Extraction already in progress or completed.",
            "document_id": document_id,
            "status": job.status
        }

    if wait:
        # Synchronous execution
        await pipeline_orchestrator.execute_pipeline(document_id)
        if job.status == ProcessingStep.FAILED:
            raise HTTPException(status_code=500, detail=job.error_message or "Extraction failed")
        return job.result

    # Asynchronous background execution
    background_tasks.add_task(pipeline_orchestrator.execute_pipeline, document_id)

    return {
        "message": "Extraction pipeline initiated.",
        "document_id": document_id,
        "status": ProcessingStep.PENDING
    }


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(document_id: str):
    """Polls processing progress and current step."""
    job = pipeline_orchestrator.get_job(document_id)
    if not job:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentStatusResponse(
        document_id=job.document_id,
        status=job.status,
        progress_percent=job.progress,
        current_step=job.current_step,
        error_message=job.error_message
    )


@router.get("/{document_id}/result", response_model=DocumentResultResponse)
def get_document_result(document_id: str):
    """Retrieves full extraction results, confidence score, and validation status."""
    job = pipeline_orchestrator.get_job(document_id)
    if not job:
        raise HTTPException(status_code=404, detail="Document not found.")

    if job.status == ProcessingStep.FAILED:
        raise HTTPException(
            status_code=500,
            detail=job.error_message or "Extraction processing failed."
        )

    if job.status != ProcessingStep.COMPLETED or not job.result:
        raise HTTPException(
            status_code=400,
            detail=f"Extraction is not completed yet (current status: {job.status})."
        )

    return job.result


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    format: str = Query(..., pattern="^(docx|pdf)$")
):
    """Downloads generated clean typed document in DOCX or PDF format."""
    job = pipeline_orchestrator.get_job(document_id)
    if not job:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_dir = storage_service.get_document_dir(document_id)
    artifacts_dir = doc_dir / "artifacts"

    if format.lower() == "docx":
        file_path = artifacts_dir / "extracted_document.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{Path(job.filename).stem}_extracted.docx"
    else:
        file_path = artifacts_dir / "extracted_document.pdf"
        media_type = "application/pdf"
        filename = f"{Path(job.filename).stem}_extracted.pdf"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Generated {format.upper()} document not found.")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """Deletes all files and artifacts for the document."""
    deleted = storage_service.delete_document(document_id)
    if document_id in pipeline_orchestrator.jobs:
        del pipeline_orchestrator.jobs[document_id]

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {"message": "Document and artifacts permanently deleted."}
