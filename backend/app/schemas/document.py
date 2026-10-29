from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.model_a import UncertainSpan, Correction
from app.schemas.model_b import Discrepancy


class ValidationStatus(str, Enum):
    PASSED_VALIDATION = "Passed Validation"
    REQUIRES_REVIEW = "Requires Review"
    FAILED_VALIDATION = "Failed Validation"
    PROCESSING_FAILED = "Processing Failed"


class ProcessingStep(str, Enum):
    PENDING = "PENDING"
    PREPROCESSING = "PREPROCESSING"
    OCR_PROCESSING = "OCR_PROCESSING"
    TRANSCRIPTION = "TRANSCRIPTION"
    VERIFICATION = "VERIFICATION"
    ALIGNMENT_SCORING = "ALIGNMENT_SCORING"
    GENERATING_DOCS = "GENERATING_DOCS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ConfidenceBreakdown(BaseModel):
    ocr_confidence: float
    verification_agreement: float
    text_agreement: float
    completeness_score: float
    preliminary_score: float
    final_score: float
    score_label: str = "Estimated Extraction Confidence"
    status_override_applied: bool = False
    override_reason: Optional[str] = None
    weights_used: Dict[str, float] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_size: int
    page_count: int
    created_at: datetime
    status: ProcessingStep


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: ProcessingStep
    progress_percent: int
    current_step: str
    error_message: Optional[str] = None


class DocumentResultResponse(BaseModel):
    document_id: str
    filename: str
    validation_status: ValidationStatus
    confidence_score: float
    confidence_breakdown: ConfidenceBreakdown
    validation_summary: str
    why_summary: str
    proposed_transcription: str
    formatted_preview_html: str
    uncertain_spans: List[UncertainSpan] = Field(default_factory=list)
    corrections_made: List[Correction] = Field(default_factory=list)
    discrepancies: List[Discrepancy] = Field(default_factory=list)
    page_count: int = 1
    created_at: datetime
    is_mock_pipeline: bool = False
    mock_notice: Optional[str] = None
