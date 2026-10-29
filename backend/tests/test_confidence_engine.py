import pytest
from app.services.confidence_engine import ConfidenceEngine
from app.schemas.document import ValidationStatus
from app.schemas.ocr import OCRResult, OCRPage
from app.schemas.model_a import ModelAResult, ModelAPage, UncertainSpan
from app.schemas.model_b import ModelBResult, VerificationOutcome, Discrepancy, DiscrepancyType, DiscrepancySeverity
from app.schemas.comparison import TextComparisonMetrics


def test_passed_validation_clean_document(mock_clear_ocr):
    engine = ConfidenceEngine()

    model_a = ModelAResult(
        proposed_transcription=mock_clear_ocr.full_text,
        pages=[ModelAPage(page_number=1, text=mock_clear_ocr.full_text)],
        uncertain_spans=[],
        corrections_made=[]
    )

    model_b = ModelBResult(
        outcome=VerificationOutcome.VERIFIED,
        agreement_percentage=98.0,
        discrepancies=[]
    )

    comparison = TextComparisonMetrics(
        char_similarity=98.0,
        word_similarity=98.0,
        insertions=[],
        deletions=[],
        substitutions=[],
        critical_discrepancies=[],
        normalized_agreement_score=98.0,
        completeness_score=100.0
    )

    status, breakdown, summary, why = engine.evaluate(
        ocr_result=mock_clear_ocr,
        model_a=model_a,
        model_b=model_b,
        comparison=comparison,
        total_pages=1,
        processed_pages=1
    )

    assert status == ValidationStatus.PASSED_VALIDATION
    assert breakdown.final_score >= 90.0
    assert not breakdown.status_override_applied


def test_critical_discrepancy_overrides_high_score(mock_clear_ocr):
    """
    Even if numerical score is >= 90, a critical discrepancy (e.g. flipped negation)
    MUST override status and strictly prevent Passed Validation.
    """
    engine = ConfidenceEngine()

    model_a = ModelAResult(
        proposed_transcription=mock_clear_ocr.full_text,
        pages=[ModelAPage(page_number=1, text=mock_clear_ocr.full_text)],
        uncertain_spans=[],
        corrections_made=[]
    )

    # Model B reports a critical discrepancy
    model_b = ModelBResult(
        outcome=VerificationOutcome.DISCREPANCIES_FOUND,
        agreement_percentage=92.0,
        discrepancies=[
            Discrepancy(
                type=DiscrepancyType.INCORRECT_NEGATION,
                text_segment="give penicillin",
                expected_segment="do NOT give penicillin",
                severity=DiscrepancySeverity.CRITICAL,
                evidence="Word 'NOT' clearly circled in bold handwriting",
                page=1
            )
        ]
    )

    comparison = TextComparisonMetrics(
        char_similarity=95.0,
        word_similarity=95.0,
        insertions=[],
        deletions=[],
        substitutions=[],
        critical_discrepancies=["CRITICAL: Negation flipped"],
        normalized_agreement_score=95.0,
        completeness_score=100.0
    )

    status, breakdown, summary, why = engine.evaluate(
        ocr_result=mock_clear_ocr,
        model_a=model_a,
        model_b=model_b,
        comparison=comparison,
        total_pages=1,
        processed_pages=1
    )

    # Must NOT be Passed Validation!
    assert status != ValidationStatus.PASSED_VALIDATION
    assert status == ValidationStatus.REQUIRES_REVIEW
    assert breakdown.status_override_applied is True
    assert "critical discrepancy" in breakdown.override_reason.lower()


def test_unresolved_uncertain_spans_trigger_review(mock_clear_ocr):
    engine = ConfidenceEngine()

    model_a = ModelAResult(
        proposed_transcription=mock_clear_ocr.full_text,
        pages=[ModelAPage(page_number=1, text=mock_clear_ocr.full_text)],
        uncertain_spans=[
            UncertainSpan(text="illegible signature", page=1, location="bottom", reason="ink smear")
        ],
        corrections_made=[]
    )

    model_b = ModelBResult(
        outcome=VerificationOutcome.VERIFIED,
        agreement_percentage=96.0,
        discrepancies=[]
    )

    comparison = TextComparisonMetrics(
        char_similarity=96.0,
        word_similarity=96.0,
        insertions=[],
        deletions=[],
        substitutions=[],
        critical_discrepancies=[],
        normalized_agreement_score=96.0,
        completeness_score=95.0
    )

    status, breakdown, summary, why = engine.evaluate(
        ocr_result=mock_clear_ocr,
        model_a=model_a,
        model_b=model_b,
        comparison=comparison,
        total_pages=1,
        processed_pages=1
    )

    # Must require review due to unclear handwriting span
    assert status == ValidationStatus.REQUIRES_REVIEW
    assert breakdown.status_override_applied is True


def test_missing_pages_fails_validation(mock_clear_ocr):
    engine = ConfidenceEngine()

    model_a = ModelAResult(
        proposed_transcription="Only Page 1",
        pages=[ModelAPage(page_number=1, text="Only Page 1")],
        uncertain_spans=[],
        corrections_made=[]
    )

    model_b = ModelBResult(
        outcome=VerificationOutcome.VERIFIED,
        agreement_percentage=95.0,
        discrepancies=[]
    )

    comparison = TextComparisonMetrics(
        char_similarity=90.0,
        word_similarity=90.0,
        insertions=[],
        deletions=[],
        substitutions=[],
        critical_discrepancies=[],
        normalized_agreement_score=90.0,
        completeness_score=50.0
    )

    # Document has 2 pages, but only 1 was processed
    status, breakdown, summary, why = engine.evaluate(
        ocr_result=mock_clear_ocr,
        model_a=model_a,
        model_b=model_b,
        comparison=comparison,
        total_pages=2,
        processed_pages=1
    )

    assert status == ValidationStatus.FAILED_VALIDATION
    assert breakdown.status_override_applied is True
