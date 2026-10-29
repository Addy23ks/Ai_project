import asyncio
import io
import pytest
from fastapi import UploadFile, BackgroundTasks
from app.main import health_check
from app.core.config import settings
from app.services.transcription_model import transcription_service
from app.services.verification_model import verification_service
from app.services.azure_ocr import azure_ocr_service
from app.api.endpoints import (
    get_config_status,
    upload_document,
    start_extraction,
    get_document_status,
    get_document_result,
    download_document,
    delete_document
)


@pytest.fixture(autouse=True)
def force_mock_for_e2e_tests(monkeypatch):
    """Ensure e2e tests use deterministic mocked stages without network delays."""
    monkeypatch.setattr(azure_ocr_service, "endpoint", None)
    monkeypatch.setattr(azure_ocr_service, "key", None)
    monkeypatch.setattr(settings, "MODEL_A_API_KEY", None)
    monkeypatch.setattr(settings, "MODEL_B_API_KEY", None)
    monkeypatch.setattr(transcription_service.adapter, "api_key", None)
    monkeypatch.setattr(verification_service.adapter, "api_key", None)


def test_health_check():
    res = health_check()
    assert res["status"] == "healthy"
    assert "Handwritten" in res["app"]


def test_config_status():
    cfg = get_config_status()
    assert "max_upload_size_mb" in cfg
    assert "pass_threshold" in cfg
    assert cfg["pass_threshold"] == 90.0


def test_full_pipeline_upload_extract_download(sample_png_bytes):
    async def run_flow():
        # 1. Upload
        upload_file = UploadFile(
            file=io.BytesIO(sample_png_bytes),
            filename="sample_handwriting.png"
        )
        upload_res = await upload_document(upload_file)
        doc_id = upload_res.document_id
        assert doc_id is not None
        assert upload_res.filename == "sample_handwriting.png"

        # 2. Extract (wait=True)
        bg = BackgroundTasks()
        extract_res = await start_extraction(document_id=doc_id, background_tasks=bg, wait=True)
        assert extract_res.document_id == doc_id
        assert extract_res.confidence_score > 0
        assert extract_res.validation_status in [
            "Passed Validation", "Requires Review", "Failed Validation"
        ]
        assert len(extract_res.proposed_transcription) > 0

        # 3. Status
        status_res = get_document_status(doc_id)
        assert status_res.status == "COMPLETED"
        assert status_res.progress_percent == 100

        # 4. Result
        result_res = get_document_result(doc_id)
        assert result_res.document_id == doc_id
        assert result_res.confidence_breakdown is not None
        assert result_res.confidence_breakdown.score_label == "Estimated Extraction Confidence"

        # 5. Download DOCX
        docx_res = download_document(doc_id, format="docx")
        assert docx_res is not None
        assert "docx" in docx_res.filename

        # 6. Download PDF
        pdf_res = download_document(doc_id, format="pdf")
        assert pdf_res is not None
        assert "pdf" in pdf_res.filename

        # 7. Delete
        del_res = delete_document(doc_id)
        assert "deleted" in del_res["message"].lower()

    asyncio.run(run_flow())
