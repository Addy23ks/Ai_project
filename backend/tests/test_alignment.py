import pytest
from app.services.text_alignment import TextAlignmentService


def test_alignment_exact_match():
    service = TextAlignmentService()
    text = "Prescription: Albuterol 90 mcg. Date: 14 Oct 2024. Patient: Eleanor Vance."
    metrics = service.compare_texts(text, text)

    assert metrics.char_similarity == 100.0
    assert metrics.word_similarity == 100.0
    assert len(metrics.critical_discrepancies) == 0
    assert metrics.completeness_score == 100.0


def test_alignment_dropped_negation():
    service = TextAlignmentService()
    ocr_text = "Instructions: Do not give penicillin. Patient has severe allergy."
    # Model mistakenly dropped the negation "not"
    proposed_text = "Instructions: Do give penicillin. Patient has severe allergy."

    metrics = service.compare_texts(ocr_text, proposed_text)
    assert any("Negation 'not'" in d for d in metrics.critical_discrepancies)


def test_alignment_altered_number():
    service = TextAlignmentService()
    ocr_text = "Prescribe Albuterol 90 mcg inhaler."
    proposed_text = "Prescribe Albuterol 50 mcg inhaler."

    metrics = service.compare_texts(ocr_text, proposed_text)
    assert any("Number/Measurement '90'" in d or "90" in d for d in metrics.critical_discrepancies)


def test_alignment_altered_date():
    service = TextAlignmentService()
    ocr_text = "Examination date: 14 Oct 2024."
    proposed_text = "Examination date: 19 Nov 2024."

    metrics = service.compare_texts(ocr_text, proposed_text)
    assert any("14 Oct 2024" in d for d in metrics.critical_discrepancies)


def test_alignment_missing_lines():
    service = TextAlignmentService()
    ocr_text = "Line 1: First instruction.\nLine 2: Second instruction.\nLine 3: Third instruction."
    proposed_text = "Line 1: First instruction."

    metrics = service.compare_texts(ocr_text, proposed_text)
    assert metrics.completeness_score < 70.0
    assert len(metrics.deletions) > 0
