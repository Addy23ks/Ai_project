from app.schemas.ocr import OCRWord, OCRLine, OCRPage, OCRResult
from app.schemas.model_a import UncertainSpan, Correction, ModelAPage, ModelAResult
from app.schemas.model_b import DiscrepancySeverity, DiscrepancyType, Discrepancy, VerificationOutcome, ModelBResult
from app.schemas.comparison import AlignmentFinding, TextComparisonMetrics
from app.schemas.document import (
    ValidationStatus,
    ProcessingStep,
    ConfidenceBreakdown,
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentResultResponse,
)

__all__ = [
    "OCRWord",
    "OCRLine",
    "OCRPage",
    "OCRResult",
    "UncertainSpan",
    "Correction",
    "ModelAPage",
    "ModelAResult",
    "DiscrepancySeverity",
    "DiscrepancyType",
    "Discrepancy",
    "VerificationOutcome",
    "ModelBResult",
    "AlignmentFinding",
    "TextComparisonMetrics",
    "ValidationStatus",
    "ProcessingStep",
    "ConfidenceBreakdown",
    "DocumentUploadResponse",
    "DocumentStatusResponse",
    "DocumentResultResponse",
]
