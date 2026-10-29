import re
from typing import List, Set, Tuple, Dict, Any
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from app.schemas.comparison import TextComparisonMetrics, AlignmentFinding

# Critical negation words that must never be flipped
NEGATION_TOKENS = {
    "not", "no", "never", "none", "without", "neither", "nor",
    "denied", "denies", "absent", "negative", "discontinued", "refused"
}

# Regex patterns for critical tokens
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:%|mg|mcg|ml|kg|g|mmHg|bpm)?\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}|\d{4})\b", re.IGNORECASE)
ID_PATTERN = re.compile(r"\b[A-Z]{1,4}-\d{3,8}\b")


class TextAlignmentService:
    def __init__(self):
        pass

    def _normalize_for_comparison(self, text: str) -> str:
        """
        Non-destructive normalization used ONLY for comparison:
        - Collapses repeated whitespace
        - Standardizes line breaks
        Preserves original casing and critical punctuation.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = " ".join(lines)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _extract_critical_tokens(self, text: str) -> Dict[str, Set[str]]:
        """Extracts critical fields: numbers, dates, IDs, and negations."""
        words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        negations = words.intersection(NEGATION_TOKENS)

        numbers = set(NUMBER_PATTERN.findall(text))
        dates = set(DATE_PATTERN.findall(text))
        ids = set(ID_PATTERN.findall(text))

        return {
            "negations": negations,
            "numbers": numbers,
            "dates": dates,
            "ids": ids
        }

    def compare_texts(
        self,
        ocr_text: str,
        proposed_text: str,
        expected_page_count: int = 1,
        processed_page_count: int = 1
    ) -> TextComparisonMetrics:
        """
        Performs deterministic sequence alignment and similarity measurement.
        """
        norm_ocr = self._normalize_for_comparison(ocr_text)
        norm_prop = self._normalize_for_comparison(proposed_text)

        if not norm_ocr and not norm_prop:
            return TextComparisonMetrics(
                char_similarity=100.0,
                word_similarity=100.0,
                insertions=[],
                deletions=[],
                substitutions=[],
                critical_discrepancies=[],
                normalized_agreement_score=100.0,
                completeness_score=100.0
            )

        if not norm_ocr or not norm_prop:
            return TextComparisonMetrics(
                char_similarity=0.0,
                word_similarity=0.0,
                insertions=["All text missing" if not norm_prop else "Entirely new text"],
                deletions=[],
                substitutions=[],
                critical_discrepancies=["Document content missing or empty"],
                normalized_agreement_score=0.0,
                completeness_score=0.0
            )

        # 1. Character-level similarity via normalized Levenshtein ratio
        char_sim = fuzz.ratio(norm_ocr, norm_prop)

        # 2. Token-level similarity
        word_sim = fuzz.token_sort_ratio(norm_ocr, norm_prop)

        # 3. Word diff analysis
        ocr_words = norm_ocr.split()
        prop_words = norm_prop.split()

        ocr_word_set = set(ocr_words)
        prop_word_set = set(prop_words)

        insertions = list(prop_word_set - ocr_word_set)[:15]
        deletions = list(ocr_word_set - prop_word_set)[:15]

        # 4. Critical Token Comparison
        crit_ocr = self._extract_critical_tokens(norm_ocr)
        crit_prop = self._extract_critical_tokens(norm_prop)

        critical_discrepancies: List[str] = []

        # Check for dropped or invented negations
        neg_diff = crit_ocr["negations"] ^ crit_prop["negations"]
        for neg in neg_diff:
            if neg in crit_ocr["negations"]:
                critical_discrepancies.append(f"CRITICAL: Negation '{neg}' present in OCR is omitted in transcription.")
            else:
                critical_discrepancies.append(f"CRITICAL: Negation '{neg}' introduced in transcription without OCR support.")

        # Check for dropped numbers or dates
        num_dropped = crit_ocr["numbers"] - crit_prop["numbers"]
        for num in num_dropped:
            critical_discrepancies.append(f"MATERIAL: Number/Measurement '{num}' in OCR missing from transcription.")

        date_dropped = crit_ocr["dates"] - crit_prop["dates"]
        for dt in date_dropped:
            critical_discrepancies.append(f"MATERIAL: Date '{dt}' in OCR missing from transcription.")

        # 5. Completeness Score
        # Accounts for page coverage and ratio of words transcribed
        page_coverage = min(1.0, processed_page_count / max(1, expected_page_count))
        length_ratio = min(1.0, len(prop_words) / max(1, len(ocr_words)))
        completeness = round(page_coverage * length_ratio * 100.0, 2)

        # 6. Normalized Agreement Score
        # Combines char similarity and token similarity
        norm_agreement = round((char_sim * 0.4 + word_sim * 0.6), 2)

        return TextComparisonMetrics(
            char_similarity=round(float(char_sim), 2),
            word_similarity=round(float(word_sim), 2),
            insertions=insertions,
            deletions=deletions,
            substitutions=[],
            critical_discrepancies=critical_discrepancies,
            normalized_agreement_score=norm_agreement,
            completeness_score=completeness
        )


text_alignment_service = TextAlignmentService()
