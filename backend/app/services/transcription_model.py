import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.ocr import OCRResult
from app.schemas.model_a import ModelAResult, ModelAPage, UncertainSpan, Correction
from app.services.llm_adapter import VisionLLMAdapter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MODEL_A = (
    "You are a conservative handwritten document transcription specialist. "
    "Transcribe the original handwriting faithfully. Use the OCR result as a reference, not as unquestionable truth. "
    "Correct only errors supported by visible evidence in the source image. "
    "Preserve names, dates, numbers, amounts, units, identifiers, abbreviations, negations and the original meaning. "
    "Do not paraphrase, summarize, invent missing text or silently correct unusual grammar. "
    "Preserve meaningful paragraph boundaries, lists and headings where visible. "
    "If any text is ambiguous, record the uncertain segment and its page and approximate location. "
    "Do not guess when the handwriting cannot be read reliably. "
    "Return structured JSON containing the proposed transcription, page-level content, uncertain spans, "
    "corrections made and their evidence."
)


class TranscriptionModelService:
    def __init__(self):
        self.adapter = VisionLLMAdapter(
            provider=settings.MODEL_A_PROVIDER,
            api_key=settings.MODEL_A_API_KEY,
            endpoint=settings.MODEL_A_ENDPOINT,
            deployment_or_model=settings.MODEL_A_DEPLOYMENT
        )

    async def transcribe(
        self,
        page_images: List[Path],
        ocr_result: OCRResult
    ) -> ModelAResult:
        """
        Executes Model A (Transcription Correction).
        """
        if not self.adapter.is_configured:
            if settings.ALLOW_DEV_MOCK_FALLBACK:
                logger.warning("Model A API key not configured. Using development mock transcription.")
                return self._generate_dev_mock_transcription(ocr_result)
            else:
                raise ValueError("Model A is not configured. Set MODEL_A_API_KEY in .env.")

        user_prompt = f"""
SOURCE DOCUMENT ANALYSIS:
Pages to process: {len(page_images)}
Primary OCR Extracted Text:
\"\"\"
{ocr_result.full_text}
\"\"\"

OCR Word-Weighted Confidence: {ocr_result.word_weighted_confidence}%

INSTRUCTIONS:
1. Examine the attached page image(s) closely.
2. Produce a faithful, conservative typed transcription.
3. If handwriting is illegible or faint, DO NOT invent text. Clearly mark uncertain spans.
4. Output must be valid JSON adhering strictly to this schema:
{{
  "proposed_transcription": "Full typed document transcription preserving paragraph breaks and headings",
  "pages": [
    {{"page_number": 1, "text": "Page 1 transcription text"}}
  ],
  "uncertain_spans": [
    {{"text": "unclear word/phrase", "page": 1, "location": "approximate position", "reason": "why unclear"}}
  ],
  "corrections_made": [
    {{"original_ocr": "ocr text", "corrected": "corrected text", "reason": "why corrected", "evidence": "visual clue in image", "page": 1}}
  ]
}}
"""
        # For multi-page, we pass the primary page or first page image
        primary_image = page_images[0] if page_images else None
        
        try:
            resp_json = await self.adapter.call_vision_chat(
                system_prompt=SYSTEM_PROMPT_MODEL_A,
                user_prompt=user_prompt,
                image_path=primary_image
            )
            return self._parse_model_a_json(resp_json)
        except Exception as e:
            logger.error(f"Model A execution failed: {str(e)}")
            if settings.ALLOW_DEV_MOCK_FALLBACK:
                logger.info("Falling back to dev mock transcription due to execution error.")
                return self._generate_dev_mock_transcription(ocr_result)
            raise

    def _parse_model_a_json(self, data: Dict[str, Any]) -> ModelAResult:
        proposed_transcription = data.get("proposed_transcription", "")
        pages_raw = data.get("pages", [])
        uncertain_raw = data.get("uncertain_spans", [])
        corrections_raw = data.get("corrections_made", [])

        pages = [
            ModelAPage(
                page_number=p.get("page_number", 1),
                text=p.get("text", "")
            )
            for p in pages_raw
        ]
        if not pages and proposed_transcription:
            pages = [ModelAPage(page_number=1, text=proposed_transcription)]

        uncertain_spans = [
            UncertainSpan(
                text=u.get("text", ""),
                page=u.get("page", 1),
                location=u.get("location", "middle"),
                reason=u.get("reason", "unclear handwriting")
            )
            for u in uncertain_raw if u.get("text")
        ]

        corrections_made = [
            Correction(
                original_ocr=c.get("original_ocr", ""),
                corrected=c.get("corrected", ""),
                reason=c.get("reason", ""),
                evidence=c.get("evidence", ""),
                page=c.get("page", 1)
            )
            for c in corrections_raw if c.get("corrected")
        ]

        return ModelAResult(
            proposed_transcription=proposed_transcription,
            pages=pages,
            uncertain_spans=uncertain_spans,
            corrections_made=corrections_made,
            is_mock=False,
            raw_response=json.dumps(data)
        )

    def _generate_dev_mock_transcription(self, ocr_result: OCRResult) -> ModelAResult:
        """Generates realistic Model A transcription result for local development."""
        base_text = ocr_result.full_text
        pages = [ModelAPage(page_number=1, text=base_text)]
        uncertain = []
        corrections = [
            Correction(
                original_ocr="penicilin",
                corrected="penicillin",
                reason="Corrected standard medical spelling based on clear handwritten double 'l'",
                evidence="Visible double vertical loop strokes in handwriting",
                page=1
            )
        ]

        return ModelAResult(
            proposed_transcription=base_text,
            pages=pages,
            uncertain_spans=uncertain,
            corrections_made=corrections,
            is_mock=True,
            raw_response="[MOCK_RESPONSE]"
        )


transcription_service = TranscriptionModelService()
