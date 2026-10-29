from pathlib import Path
from app.services.document_generator import DocumentGeneratorService
from app.schemas.document import ValidationStatus
from app.schemas.model_a import UncertainSpan


def test_generate_docx_and_pdf(tmp_path):
    generator = DocumentGeneratorService()
    transcription = (
        "CONSULTATION NOTE\n\n"
        "Patient: Eleanor Vance\n"
        "Date: 14 Oct 2024\n\n"
        "Assessment: Patient presented with ambiguous cough."
    )
    uncertain_spans = [
        UncertainSpan(text="ambiguous", page=1, location="middle", reason="cursive stroke unclear")
    ]

    docx_path = tmp_path / "output.docx"
    pdf_path = tmp_path / "output.pdf"

    # Test DOCX
    res_docx = generator.generate_docx(
        transcription=transcription,
        uncertain_spans=uncertain_spans,
        status=ValidationStatus.REQUIRES_REVIEW,
        score=84.5,
        output_path=docx_path
    )
    assert res_docx.exists()
    assert res_docx.stat().st_size > 0

    # Test PDF
    res_pdf = generator.generate_pdf(
        transcription=transcription,
        uncertain_spans=uncertain_spans,
        status=ValidationStatus.REQUIRES_REVIEW,
        score=84.5,
        output_path=pdf_path
    )
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 0

    # Test HTML Preview
    html_preview = generator.generate_html_preview(
        transcription=transcription,
        uncertain_spans=uncertain_spans,
        status=ValidationStatus.REQUIRES_REVIEW,
        score=84.5
    )
    assert "[UNCLEAR]" in html_preview
    assert "Eleanor Vance" in html_preview
