from typing import List, Tuple
from app.core.config import settings
from app.schemas.document import ValidationStatus, ConfidenceBreakdown
from app.schemas.ocr import OCRResult
from app.schemas.model_a import ModelAResult
from app.schemas.model_b import ModelBResult, DiscrepancySeverity
from app.schemas.comparison import TextComparisonMetrics


class ConfidenceEngine:
    def __init__(self):
        self.w_ocr = settings.WEIGHT_OCR
        self.w_verif = settings.WEIGHT_VERIFICATION
        self.w_text = settings.WEIGHT_TEXT_AGREEMENT
        self.w_comp = settings.WEIGHT_COMPLETENESS

    def calculate_verification_score(self, model_b: ModelBResult) -> float:
        """
        Calculates verification agreement from actual findings rather than
        blindly trusting self-reported numbers.
        Penalizes each critical discrepancy (-25%), material discrepancy (-10%), and minor discrepancy (-3%).
        """
        base_score = 100.0
        for d in model_b.discrepancies:
            if d.severity == DiscrepancySeverity.CRITICAL:
                base_score -= 25.0
            elif d.severity == DiscrepancySeverity.MATERIAL:
                base_score -= 10.0
            elif d.severity == DiscrepancySeverity.MINOR:
                base_score -= 3.0

        # Also blend with model B self-reported agreement if valid
        measured_score = max(0.0, min(100.0, base_score))
        return round(0.7 * measured_score + 0.3 * model_b.agreement_percentage, 2)

    def calculate_completeness_score(
        self,
        comparison: TextComparisonMetrics,
        model_a: ModelAResult,
        model_b: ModelBResult
    ) -> float:
        """
        Deducts for uncertain spans, missing segments, or dropped lines.
        """
        score = comparison.completeness_score

        # Deduct for uncertain handwriting spans in Model A
        uncertain_count = len(model_a.uncertain_spans)
        score -= (uncertain_count * 5.0)

        # Deduct for missing segments detected by Model B
        missing_count = len(model_b.missing_segments)
        score -= (missing_count * 10.0)

        return max(0.0, min(100.0, round(score, 2)))

    def evaluate(
        self,
        ocr_result: OCRResult,
        model_a: ModelAResult,
        model_b: ModelBResult,
        comparison: TextComparisonMetrics,
        total_pages: int,
        processed_pages: int
    ) -> Tuple[ValidationStatus, ConfidenceBreakdown, str, str]:
        """
        Calculates the defensible confidence score and assigns validation status.
        Returns: (status, breakdown, validation_summary, why_summary)
        """
        ocr_conf = ocr_result.word_weighted_confidence
        verif_agreement = self.calculate_verification_score(model_b)
        text_agreement = comparison.normalized_agreement_score
        completeness_score = self.calculate_completeness_score(comparison, model_a, model_b)

        # Preliminary weighted calculation
        preliminary_score = (
            self.w_ocr * ocr_conf +
            self.w_verif * verif_agreement +
            self.w_text * text_agreement +
            self.w_comp * completeness_score
        )
        preliminary_score = round(max(0.0, min(100.0, preliminary_score)), 2)
        final_score = preliminary_score

        # Check for critical conditions
        has_critical_discrepancy = any(
            d.severity == DiscrepancySeverity.CRITICAL for d in model_b.discrepancies
        ) or bool(comparison.critical_discrepancies)

        has_material_discrepancy = any(
            d.severity == DiscrepancySeverity.MATERIAL for d in model_b.discrepancies
        )

        has_unresolved_uncertainty = len(model_a.uncertain_spans) > 0
        pages_incomplete = processed_pages < total_pages

        status_override = False
        override_reason = None

        # Determine validation status with guardrails
        if pages_incomplete:
            status = ValidationStatus.FAILED_VALIDATION
            status_override = True
            override_reason = f"Document processing incomplete ({processed_pages}/{total_pages} pages processed)."
            final_score = min(final_score, 50.0)

        elif has_critical_discrepancy:
            # Critical discrepancy strictly prohibits Passed Validation
            status = ValidationStatus.REQUIRES_REVIEW if preliminary_score >= 60.0 else ValidationStatus.FAILED_VALIDATION
            status_override = True
            override_reason = "Critical discrepancy detected (negation, identifier, or key value mismatch). Automatic pass prohibited."

        elif has_material_discrepancy or has_unresolved_uncertainty:
            if preliminary_score >= settings.PASS_THRESHOLD:
                status = ValidationStatus.REQUIRES_REVIEW
                status_override = True
                override_reason = "Unresolved ambiguous handwriting spans or material discrepancies require human review."
            elif preliminary_score >= settings.REVIEW_THRESHOLD:
                status = ValidationStatus.REQUIRES_REVIEW
            else:
                status = ValidationStatus.FAILED_VALIDATION

        else:
            # Score-based assignment
            if preliminary_score >= settings.PASS_THRESHOLD:
                status = ValidationStatus.PASSED_VALIDATION
            elif preliminary_score >= settings.REVIEW_THRESHOLD:
                status = ValidationStatus.REQUIRES_REVIEW
            else:
                status = ValidationStatus.FAILED_VALIDATION

        breakdown = ConfidenceBreakdown(
            ocr_confidence=round(ocr_conf, 2),
            verification_agreement=round(verif_agreement, 2),
            text_agreement=round(text_agreement, 2),
            completeness_score=round(completeness_score, 2),
            preliminary_score=preliminary_score,
            final_score=final_score,
            score_label="Estimated Extraction Confidence",
            status_override_applied=status_override,
            override_reason=override_reason,
            weights_used={
                "ocr_confidence": self.w_ocr,
                "verification_agreement": self.w_verif,
                "text_agreement": self.w_text,
                "completeness": self.w_comp
            }
        )

        # Construct clear summaries
        if status == ValidationStatus.PASSED_VALIDATION:
            validation_summary = (
                f"The extraction achieved a high confidence score of {final_score}% with strong OCR quality "
                f"({ocr_conf}%), full multi-model consensus ({verif_agreement}%), and zero unresolved critical discrepancies."
            )
            why_summary = "High OCR alignment, clean handwriting verification, and complete document integrity confirmed."
        elif status == ValidationStatus.REQUIRES_REVIEW:
            reasons = []
            if status_override and override_reason:
                reasons.append(override_reason)
            if has_unresolved_uncertainty:
                reasons.append(f"{len(model_a.uncertain_spans)} unclear handwriting segment(s) flagged")
            if has_critical_discrepancy:
                reasons.append("Critical discrepancies detected between OCR and independent verification")
            if not reasons:
                reasons.append(f"Confidence score of {final_score}% falls within the review threshold (70-89%)")

            validation_summary = (
                f"Document requires human verification. Confidence score: {final_score}%. "
                f"Key concerns: {'; '.join(reasons)}."
            )
            why_summary = "; ".join(reasons)
        else:
            validation_summary = (
                f"Document failed automatic validation with a low confidence score of {final_score}%. "
                f"Significant extraction errors or illegible handwriting detected."
            )
            why_summary = override_reason or "Low confidence score below acceptable acceptance threshold."

        return status, breakdown, validation_summary, why_summary


confidence_engine = ConfidenceEngine()
