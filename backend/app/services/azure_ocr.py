import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx

from app.core.config import settings
from app.schemas.ocr import OCRWord, OCRLine, OCRPage, OCRResult
from app.services.llm_adapter import VisionLLMAdapter

logger = logging.getLogger(__name__)


class AzureOCRService:
    def __init__(self):
        self.endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
        self.api_version = settings.AZURE_DOCUMENT_INTELLIGENCE_API_VERSION

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.key and not self.endpoint.startswith("https://your-"))

    async def analyze_document(
        self, file_path: Path, use_enhanced: bool = False
    ) -> OCRResult:
        """
        Executes Azure AI Document Intelligence Read model (prebuilt-read).
        Falls back to GPT-4o vision OCR if Azure credentials are absent and a Model A key is configured.
        Raises a clear error if neither is available.
        """
        if not self.is_configured:
            if settings.ALLOW_DEV_MOCK_FALLBACK:
                logger.warning(
                    "Azure Document Intelligence credentials not configured. "
                    "Attempting LLM vision fallback OCR using Model A."
                )
                return await self._llm_vision_ocr_fallback(file_path)
            else:
                raise ValueError(
                    "Azure Document Intelligence credentials are not configured. "
                    "Please set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY in .env."
                )

        clean_endpoint = self.endpoint.rstrip("/")
        url = f"{clean_endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version={self.api_version}&features=ocrHighResolution"

        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/octet-stream"
        }

        with open(file_path, "rb") as f:
            data = f.read()

        async with httpx.AsyncClient(timeout=60.0) as client:
            submit_res = await client.post(url, headers=headers, content=data)
            if submit_res.status_code != 202:
                # In older versions endpoint might use formrecognizer path
                if submit_res.status_code == 404:
                    url_legacy = f"{clean_endpoint}/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2023-07-31"
                    submit_res = await client.post(url_legacy, headers=headers, content=data)

                if submit_res.status_code not in (200, 202):
                    error_detail = submit_res.text
                    raise RuntimeError(f"Azure OCR submission failed ({submit_res.status_code}): {error_detail}")

            operation_url = submit_res.headers.get("Operation-Location")
            if not operation_url:
                raise RuntimeError("Azure OCR did not return an Operation-Location header for polling.")

            # Poll for result
            poll_headers = {"Ocp-Apim-Subscription-Key": self.key}
            max_attempts = 45
            for _ in range(max_attempts):
                await asyncio.sleep(1.5)
                poll_res = await client.get(operation_url, headers=poll_headers)
                if poll_res.status_code != 200:
                    continue

                poll_json = poll_res.json()
                status = poll_json.get("status")

                if status == "succeeded":
                    return self._parse_azure_response(poll_json.get("analyzeResult", {}))
                elif status == "failed":
                    error_msg = poll_json.get("error", {}).get("message", "Unknown Azure error")
                    raise RuntimeError(f"Azure OCR processing failed: {error_msg}")

            raise TimeoutError("Timed out waiting for Azure Document Intelligence response.")

    def _parse_azure_response(self, analyze_result: Dict[str, Any]) -> OCRResult:
        """Parses the raw Azure Document Intelligence analyzeResult."""
        raw_pages = analyze_result.get("pages", [])
        parsed_pages: List[OCRPage] = []

        total_words = 0
        words_with_confidence = 0
        missing_confidence_count = 0
        confidence_sum = 0.0
        warnings: List[str] = []

        for p_idx, p in enumerate(raw_pages):
            page_num = p.get("pageNumber", p_idx + 1)
            width = float(p.get("width", 0))
            height = float(p.get("height", 0))
            unit = p.get("unit", "pixel")

            raw_words = p.get("words", [])
            raw_lines = p.get("lines", [])

            page_words: List[OCRWord] = []
            page_conf_sum = 0.0
            page_words_with_conf = 0

            for w in raw_words:
                text = w.get("content", "")
                conf = w.get("confidence")
                polygon = w.get("polygon")
                span = None
                if "span" in w:
                    span = (w["span"].get("offset", 0), w["span"].get("length", 0))

                if conf is not None:
                    # Convert to 0-100 scale
                    scaled_conf = float(conf) * 100.0 if float(conf) <= 1.0 else float(conf)
                    confidence_sum += scaled_conf
                    words_with_confidence += 1
                    page_conf_sum += scaled_conf
                    page_words_with_conf += 1
                else:
                    scaled_conf = None
                    missing_confidence_count += 1

                total_words += 1
                page_words.append(
                    OCRWord(
                        text=text,
                        confidence=scaled_conf,
                        polygon=polygon,
                        span=span
                    )
                )

            page_lines: List[OCRLine] = []
            line_texts: List[str] = []
            for l in raw_lines:
                content = l.get("content", "")
                line_texts.append(content)
                l_conf = None
                # Calculate line average confidence from its words if available
                l_polygon = l.get("polygon")
                page_lines.append(
                    OCRLine(
                        text=content,
                        confidence=l_conf,
                        polygon=l_polygon
                    )
                )

            page_avg_conf = (page_conf_sum / page_words_with_conf) if page_words_with_conf > 0 else 0.0
            page_text = "\n".join(line_texts)

            parsed_pages.append(
                OCRPage(
                    page_number=page_num,
                    width=width,
                    height=height,
                    unit=unit,
                    lines=page_lines,
                    words=page_words,
                    page_text=page_text,
                    word_weighted_confidence=round(page_avg_conf, 2),
                    is_handwritten=True
                )
            )

        if missing_confidence_count > 0:
            warnings.append(
                f"{missing_confidence_count} words lacked direct OCR confidence values (missing confidence); calculated using measured words only."
            )

        overall_conf = (confidence_sum / words_with_confidence) if words_with_confidence > 0 else 0.0

        full_text = analyze_result.get("content", "")
        if not full_text:
            full_text = "\n\n".join([p.page_text for p in parsed_pages])

        return OCRResult(
            full_text=full_text,
            pages=parsed_pages,
            word_weighted_confidence=round(overall_conf, 2),
            total_words=total_words,
            words_with_confidence=words_with_confidence,
            missing_confidence_count=missing_confidence_count,
            is_mock=False,
            warnings=warnings
        )

    async def _llm_vision_ocr_fallback(self, file_path: Path) -> OCRResult:
        """
        Uses GPT-4o vision (Model A configuration) to extract text from the document image
        when Azure Document Intelligence is not configured.
        Returns results in the same OCRResult schema so the rest of the pipeline is unaffected.
        """
        adapter = VisionLLMAdapter(
            provider=settings.MODEL_A_PROVIDER,
            api_key=settings.MODEL_A_API_KEY,
            endpoint=settings.MODEL_A_ENDPOINT,
            deployment_or_model=settings.MODEL_A_DEPLOYMENT,
        )

        if not adapter.is_configured:
            if settings.ALLOW_DEV_MOCK_FALLBACK:
                logger.warning("Neither Azure nor LLM credentials configured. Using development mock OCR.")
                return self._generate_dev_mock_ocr(file_path)
            raise ValueError(
                "Azure Document Intelligence is not configured and no LLM API key is available as fallback. "
                "Please configure either AZURE_DOCUMENT_INTELLIGENCE_KEY or MODEL_A_API_KEY in .env."
            )

        system_prompt = (
            "You are an OCR engine. Your sole task is to read the text visible in the provided document image "
            "exactly as written — including handwriting, printed text, numbers, punctuation, and layout. "
            "Do NOT correct spelling, interpret abbreviations, or paraphrase. "
            "Transcribe every line in the order it appears, top to bottom. "
            "If a word or section is genuinely unreadable, write [UNCLEAR] in its place. "
            "Respond with a JSON object in this exact format:\n"
            "{\n"
            '  "lines": ["line 1 text", "line 2 text", ...],\n'
            '  "estimated_confidence": <number 0-100 reflecting how readable the document was>\n'
            "}"
        )

        user_prompt = (
            "Please transcribe all text visible in this document image. "
            "Return every line in order, exactly as written."
        )

        logger.info(f"LLM vision OCR fallback: sending {file_path.name} to {adapter.model}")

        try:
            response = await adapter.call_vision_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_path=file_path,
            )
        except Exception as e:
            raise RuntimeError(f"LLM vision OCR fallback failed: {str(e)}")

        raw_lines: List[str] = response.get("lines", [])
        estimated_conf: float = float(response.get("estimated_confidence", 80.0))

        if not raw_lines:
            raise ValueError("LLM vision OCR fallback returned no text lines. The document may be unreadable.")

        # Build OCRResult in the same structure as Azure responses
        page_words: List[OCRWord] = []
        page_lines: List[OCRLine] = []
        total_words = 0
        conf_sum = 0.0

        for line_str in raw_lines:
            if not line_str.strip():
                continue
            words_in_line = line_str.split()
            line_ocr_words: List[OCRWord] = []
            for w in words_in_line:
                # Mark [UNCLEAR] tokens with lower per-word confidence
                word_conf = 40.0 if "[UNCLEAR]" in w else estimated_conf
                conf_sum += word_conf
                total_words += 1
                ocr_w = OCRWord(text=w, confidence=word_conf)
                line_ocr_words.append(ocr_w)
                page_words.append(ocr_w)
            page_lines.append(OCRLine(text=line_str, words=line_ocr_words))

        weighted_conf = round(conf_sum / total_words, 2) if total_words > 0 else estimated_conf
        full_text = "\n".join(raw_lines)

        page = OCRPage(
            page_number=1,
            width=0.0,
            height=0.0,
            lines=page_lines,
            words=page_words,
            page_text=full_text,
            word_weighted_confidence=weighted_conf,
            is_handwritten=True,
        )

        return OCRResult(
            full_text=full_text,
            pages=[page],
            word_weighted_confidence=weighted_conf,
            total_words=total_words,
            words_with_confidence=total_words,
            missing_confidence_count=0,
            is_mock=False,
            warnings=[
                f"[LLM FALLBACK] Azure Document Intelligence is not configured. "
                f"OCR performed by {adapter.model} vision model."
            ],
        )

    def _generate_dev_mock_ocr(self, file_path: Path) -> OCRResult:
        """
        Generates a deterministic simulated OCR result for offline local development and tests
        when neither Azure nor LLM keys are provided.
        """
        mock_text = (
            "Patient Consultation Note\n"
            "Date: 14 Oct 2024\n"
            "Patient: Eleanor Vance (ID: EV-88219)\n\n"
            "Chief Complaint: Persistent cough and mild dyspnea for 3 weeks.\n"
            "History: No history of smoking. Prior allergy to penicillin noted in 2018.\n"
            "Examination: BP 124/82 mmHg, HR 76 bpm, SpO2 97% on room air.\n"
            "Chest clear to auscultation bilaterally. No audible wheezes or crackles.\n\n"
            "Assessment & Plan:\n"
            "1. Upper respiratory tract post-viral hyperreactivity.\n"
            "2. Prescribe Albuterol inhaler 90 mcg 2 puffs PRN.\n"
            "3. Do NOT initiate oral corticosteroids at this time.\n"
            "4. Follow-up in clinic in 14 days if symptoms persist."
        )

        lines = [line for line in mock_text.split("\n") if line.strip()]
        page_words: List[OCRWord] = []
        page_lines: List[OCRLine] = []

        total_words = 0
        conf_sum = 0.0

        for line_str in lines:
            words_in_line = line_str.split()
            line_ocr_words: List[OCRWord] = []
            for w in words_in_line:
                conf = 88.5 if len(w) > 6 else 94.0
                if "NOT" in w or "90" in w:
                    conf = 85.0
                conf_sum += conf
                total_words += 1
                ocr_w = OCRWord(text=w, confidence=conf)
                line_ocr_words.append(ocr_w)
                page_words.append(ocr_w)

            page_lines.append(OCRLine(text=line_str, words=line_ocr_words))

        weighted_conf = conf_sum / total_words if total_words > 0 else 91.5

        page = OCRPage(
            page_number=1,
            width=1700.0,
            height=2200.0,
            lines=page_lines,
            words=page_words,
            page_text=mock_text,
            word_weighted_confidence=round(weighted_conf, 2),
            is_handwritten=True,
        )

        return OCRResult(
            full_text=mock_text,
            pages=[page],
            word_weighted_confidence=round(weighted_conf, 2),
            total_words=total_words,
            words_with_confidence=total_words,
            missing_confidence_count=0,
            is_mock=True,
            warnings=["[DEV MODE] Simulated OCR extraction used because Azure Document Intelligence and LLM are not configured."],
        )


azure_ocr_service = AzureOCRService()
