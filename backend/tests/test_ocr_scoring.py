import pytest
from app.services.azure_ocr import AzureOCRService
from app.schemas.ocr import OCRWord, OCRPage, OCRResult


def test_word_weighted_ocr_confidence_calculation():
    service = AzureOCRService()
    # Mock Azure analyzeResult with known confidences
    mock_analyze_result = {
        "content": "Patient Eleanor Vance",
        "pages": [
            {
                "pageNumber": 1,
                "width": 1000,
                "height": 800,
                "unit": "pixel",
                "words": [
                    {"content": "Patient", "confidence": 0.90},
                    {"content": "Eleanor", "confidence": 0.80},
                    {"content": "Vance", "confidence": 1.00}
                ],
                "lines": [
                    {"content": "Patient Eleanor Vance"}
                ]
            }
        ]
    }

    result = service._parse_azure_response(mock_analyze_result)
    assert result.total_words == 3
    assert result.words_with_confidence == 3
    assert result.missing_confidence_count == 0
    # Average of 90, 80, 100 is 90.0
    assert result.word_weighted_confidence == 90.0


def test_handle_missing_confidence_values():
    service = AzureOCRService()
    mock_analyze_result = {
        "content": "Patient Eleanor Vance",
        "pages": [
            {
                "pageNumber": 1,
                "words": [
                    {"content": "Patient", "confidence": 0.90},
                    {"content": "Eleanor", "confidence": None},  # Missing confidence!
                    {"content": "Vance", "confidence": 0.80}
                ],
                "lines": []
            }
        ]
    }

    result = service._parse_azure_response(mock_analyze_result)
    assert result.total_words == 3
    assert result.words_with_confidence == 2
    assert result.missing_confidence_count == 1
    # Average of measured words (90 + 80) / 2 = 85.0
    assert result.word_weighted_confidence == 85.0
    assert len(result.warnings) > 0
    assert "missing" in result.warnings[0].lower()
