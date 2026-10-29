import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from app.schemas.document import (
    ProcessingStep,
    ValidationStatus,
    DocumentStatusResponse,
    DocumentResultResponse,
    ConfidenceBreakdown
)
from app.services.file_storage import storage_service
from app.services.preprocessing import preprocessing_service
from app.services.azure_ocr import azure_ocr_service
from app.services.transcription_model import transcription_service
from app.services.verification_model import verification_service
from app.services.text_alignment import text_alignment_service
from app.services.confidence_engine import confidence_engine
from app.services.document_generator import document_generator

logger = logging.getLogger(__name__)


class PipelineJob:
    def __init__(self, document_id: str, filename: str, file_path: Path):
        self.document_id = document_id
        self.filename = filename
        self.file_path = file_path
        self.status = ProcessingStep.PENDING
        self.progress = 0
        self.current_step = "Initialized"
        self.error_message: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.result: Optional[DocumentResultResponse] = None


class PipelineOrchestrator:
    def __init__(self):
        # In-memory job tracker for quick polling
        self.jobs: Dict[str, PipelineJob] = {}

    def register_job(self, document_id: str, filename: str, file_path: Path) -> PipelineJob:
        job = PipelineJob(document_id, filename, file_path)
        self.jobs[document_id] = job
        return job

    def get_job(self, document_id: str) -> Optional[PipelineJob]:
        return self.jobs.get(document_id)

    async def execute_pipeline(self, document_id: str):
        job = self.get_job(document_id)
        if not job:
            logger.error(f"Job {document_id} not found")
            return

        doc_dir = storage_service.get_document_dir(document_id)
        artifacts_dir = doc_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        try:
            # Step 1: Preprocessing
            job.status = ProcessingStep.PREPROCESSING
            job.progress = 15
            job.current_step = "Extracting pages and preprocessing image (orientation, deskew, contrast, denoise)"

            extracted_pages = preprocessing_service.extract_pages_from_document(job.file_path, doc_dir)
            total_pages = len(extracted_pages)

            preprocessed_pages = []
            for page_num, page_path in extracted_pages:
                preproc_info = preprocessing_service.preprocess_page_image(page_path)
                preprocessed_pages.append(preproc_info)

            # Step 2: OCR Processing
            job.status = ProcessingStep.OCR_PROCESSING
            job.progress = 35
            job.current_step = "Executing Azure AI Document Intelligence Read OCR"

            # Use primary enhanced image or source file
            primary_image_path = preprocessed_pages[0]["enhanced_path"] if preprocessed_pages else job.file_path
            ocr_result = await azure_ocr_service.analyze_document(primary_image_path)

            # Step 3: Model A Transcription
            job.status = ProcessingStep.TRANSCRIPTION
            job.progress = 55
            job.current_step = "Model A: Conservative transcription and structural analysis"

            page_images_to_pass = [p["enhanced_path"] for p in preprocessed_pages]
            model_a_result = await transcription_service.transcribe(page_images_to_pass, ocr_result)

            # Step 4: Model B Verification
            job.status = ProcessingStep.VERIFICATION
            job.progress = 75
            job.current_step = "Model B: Independent character-by-character forensic verification"

            # Pass original untreated images to Model B for unassisted inspection
            orig_images_to_pass = [p["original_path"] for p in preprocessed_pages]
            model_b_result = await verification_service.verify(orig_images_to_pass, ocr_result, model_a_result)

            # Step 5: Alignment & Scoring
            job.status = ProcessingStep.ALIGNMENT_SCORING
            job.progress = 85
            job.current_step = "Comparing sequences and calculating defensible confidence score"

            comparison_metrics = text_alignment_service.compare_texts(
                ocr_text=ocr_result.full_text,
                proposed_text=model_a_result.proposed_transcription,
                expected_page_count=total_pages,
                processed_page_count=len(model_a_result.pages)
            )

            status, breakdown, val_summary, why_summary = confidence_engine.evaluate(
                ocr_result=ocr_result,
                model_a=model_a_result,
                model_b=model_b_result,
                comparison=comparison_metrics,
                total_pages=total_pages,
                processed_pages=len(model_a_result.pages)
            )

            # Step 6: Document Generation
            job.status = ProcessingStep.GENERATING_DOCS
            job.progress = 95
            job.current_step = "Generating typed DOCX, PDF, and in-browser preview"

            docx_path = artifacts_dir / "extracted_document.docx"
            pdf_path = artifacts_dir / "extracted_document.pdf"

            document_generator.generate_docx(
                transcription=model_a_result.proposed_transcription,
                uncertain_spans=model_a_result.uncertain_spans,
                status=status,
                score=breakdown.final_score,
                output_path=docx_path
            )

            document_generator.generate_pdf(
                transcription=model_a_result.proposed_transcription,
                uncertain_spans=model_a_result.uncertain_spans,
                status=status,
                score=breakdown.final_score,
                output_path=pdf_path
            )

            preview_html = document_generator.generate_html_preview(
                transcription=model_a_result.proposed_transcription,
                uncertain_spans=model_a_result.uncertain_spans,
                status=status,
                score=breakdown.final_score
            )

            # Check if any stage was simulated
            is_mock_pipeline = ocr_result.is_mock or model_a_result.is_mock or model_b_result.is_mock
            mock_notice = None
            if is_mock_pipeline:
                mock_notice = "DEVELOPMENT NOTICE: Ran using simulated models because external Azure/LLM credentials are not configured in .env."

            # Finalize Result
            job.result = DocumentResultResponse(
                document_id=document_id,
                filename=job.filename,
                validation_status=status,
                confidence_score=breakdown.final_score,
                confidence_breakdown=breakdown,
                validation_summary=val_summary,
                why_summary=why_summary,
                proposed_transcription=model_a_result.proposed_transcription,
                formatted_preview_html=preview_html,
                uncertain_spans=model_a_result.uncertain_spans,
                corrections_made=model_a_result.corrections_made,
                discrepancies=model_b_result.discrepancies,
                page_count=total_pages,
                created_at=job.created_at,
                is_mock_pipeline=is_mock_pipeline,
                mock_notice=mock_notice
            )

            job.status = ProcessingStep.COMPLETED
            job.progress = 100
            job.current_step = "Completed successfully"

        except Exception as e:
            logger.exception(f"Pipeline failed for document {document_id}: {str(e)}")
            job.status = ProcessingStep.FAILED
            job.error_message = str(e)
            job.current_step = f"Processing Failed: {str(e)}"


pipeline_orchestrator = PipelineOrchestrator()
