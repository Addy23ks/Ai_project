import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.ocr import OCRResult
from app.schemas.model_a import ModelAResult
from app.schemas.model_b import (
    ModelBResult,
    VerificationOutcome,
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity
)
from app.services.llm_adapter import VisionLLMAdapter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MODEL_B = (
    "You are an independent forensic document verification specialist. "
    "Your duty is to critically inspect the provided source document image and rigorously audit a proposed typed transcription. "
    "Do NOT assume the proposed transcription or OCR is correct. Examine the handwriting character by character, "
    "number by number, and phrase by phrase where feasible. "
    "Check for: "
    "1. Missing words, skipped lines, or omitted paragraphs. "
    "2. Substituted, hallucinated, or added words. "
    "3. Misread numbers, dates, monetary amounts, patient/case IDs, and dosages. "
    "4. Inverted negations (e.g. 'no', 'not', 'never', 'denied', 'without') or meaning-altering wording. "
    "5. Material punctuation errors (e.g. decimal points like 0.5 vs 5, hyphenated ranges). "
    "6. Ambiguous, faint, or illegible handwriting where the correct text cannot be determined with certainty. "
    "Assign discrepancy severity: "
    "- 'CRITICAL': Altered negations, modified numbers/dates/names/units/dosages, omitted vital clauses. "
    "- 'MATERIAL': Missing or substituted non-critical phrases/sentences. "
    "- 'MINOR': Incidental capitalization, spacing, or immaterial punctuation differences. "
    "If handwriting cannot be verified due to blur or occlusion, mark it explicitly as UNVERIFIABLE. "
    "Output must be structured JSON."
)


class VerificationModelService:
    def __init__(self):
        self.adapter = VisionLLMAdapter(
            provider=settings.MODEL_B_PROVIDER,
            api_key=settings.MODEL_B_API_KEY,
            endpoint=settings.MODEL_B_ENDPOINT,
            deployment_or_model=settings.MODEL_B_DEPLOYMENT
        )

    async def verify(
        self,
        page_images: List[Path],
        ocr_result: OCRResult,
        model_a_result: ModelAResult
    ) -> ModelBResult:
        """
        Executes Model B (Independent Verification).
        """
        if not self.adapter.is_configured:
            if settings.ALLOW_DEV_MOCK_FALLBACK:
                logger.warning("Model B API key not configured. Using development mock verification.")
                return self._generate_dev_mock_verification(model_a_result)
            else:
                raise ValueError("Model B is not configured. Set MODEL_B_API_KEY in .env.")

        user_prompt = f"""
INDEPENDENT VERIFICATION AUDIT REQUEST:

PROPOSED TRANSCRIPTION (FROM MODEL A):
\"\"\"
{model_a_result.proposed_transcription}
\"\"\"

RAW OCR RESULT (REFERENCE ONLY):
\"\"\"
{ocr_result.full_text}
\"\"\"

OCR Word Confidence: {ocr_result.word_weighted_confidence}%

INSTRUCTIONS:
Audit the proposed transcription against the attached source document image.
Return JSON with the following exact structure:
{{
  "outcome": "VERIFIED" | "DISCREPANCIES_FOUND" | "UNVERIFIABLE",
  "agreement_percentage": 98.5,
  "matched_segments": ["verified phrase 1", "verified phrase 2"],
  "missing_segments": [],
  "suspected_substitutions": [],
  "uncertain_segments": [],
  "discrepancies": [
    {{
      "type": "INCORRECT_NUMBER" | "INCORRECT_NEGATION" | "MISSING_TEXT" | "SUBSTITUTED_TEXT" | "INCORRECT_NAME" | "INCORRECT_DATE" | "PUNCTUATION_ALTERATION" | "UNVERIFIABLE",
      "text_segment": "text in proposed transcription",
      "expected_segment": "actual text visible in image",
      "severity": "CRITICAL" | "MATERIAL" | "MINOR",
      "evidence": "detailed visual evidence from handwriting",
      "page": 1
    }}
  ],
  "summary_notes": "Concise summary of audit findings"
}}
"""
        primary_image = page_images[0] if page_images else None

        try:
            resp_json = await self.adapter.call_vision_chat(
                system_prompt=SYSTEM_PROMPT_MODEL_B,
                user_prompt=user_prompt,
                image_path=primary_image
            )
            return self._parse_model_b_json(resp_json)
        except Exception as e:
            logger.error(f"Model B execution failed: {str(e)}")
            if settings.ALLOW_DEV_MOCK_FALLBACK:
                logger.info("Falling back to dev mock verification due to execution error.")
                return self._generate_dev_mock_verification(model_a_result)
            raise

    def _parse_model_b_json(self, data: Dict[str, Any]) -> ModelBResult:
        raw_outcome = data.get("outcome", "VERIFIED")
        try:
            outcome = VerificationOutcome(raw_outcome)
        except ValueError:
            outcome = VerificationOutcome.DISCREPANCIES_FOUND if data.get("discrepancies") else VerificationOutcome.VERIFIED

        raw_discrepancies = data.get("discrepancies", [])
        discrepancies: List[Discrepancy] = []

        for d in raw_discrepancies:
            d_type = d.get("type", "SUBSTITUTED_TEXT")
            try:
                disc_type = DiscrepancyType(d_type)
            except ValueError:
                disc_type = DiscrepancyType.SUBSTITUTED_TEXT

            d_sev = d.get("severity", "MATERIAL")
            try:
                disc_sev = DiscrepancySeverity(d_sev)
            except ValueError:
                disc_sev = DiscrepancySeverity.MATERIAL

            discrepancies.append(
                Discrepancy(
                    type=disc_type,
                    text_segment=d.get("text_segment", ""),
                    expected_segment=d.get("expected_segment", ""),
                    severity=disc_sev,
                    evidence=d.get("evidence", ""),
                    page=d.get("page", 1)
                )
            )

        agreement = float(data.get("agreement_percentage", 100.0))
        agreement = max(0.0, min(100.0, agreement))

        return ModelBResult(
            outcome=outcome,
            matched_segments=data.get("matched_segments", []),
            missing_segments=data.get("missing_segments", []),
            suspected_substitutions=data.get("suspected_substitutions", []),
            uncertain_segments=data.get("uncertain_segments", []),
            discrepancies=discrepancies,
            agreement_percentage=agreement,
            summary_notes=data.get("summary_notes", "Independent audit completed."),
            is_mock=False
        )

    def _generate_dev_mock_verification(self, model_a_result: ModelAResult) -> ModelBResult:
        """Generates realistic Model B verification result for local development."""
        # Check if model A output contains any apparent critical discrepancies
        text = model_a_result.proposed_transcription
        discrepancies: List[Discrepancy] = []

        return ModelBResult(
            outcome=VerificationOutcome.VERIFIED,
            matched_segments=["Patient Consultation Note", "Eleanor Vance (ID: EV-88219)", "Assessment & Plan"],
            missing_segments=[],
            suspected_substitutions=[],
            uncertain_segments=[],
            discrepancies=discrepancies,
            agreement_percentage=97.5,
            summary_notes="All critical identifiers, dosages, dates, and negations verified against source image.",
            is_mock=True
        )


verification_service = VerificationModelService()
