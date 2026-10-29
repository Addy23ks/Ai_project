import io
import pytest
from fastapi import HTTPException
from app.services.file_storage import FileStorageService


def test_validate_valid_signatures(sample_png_bytes, sample_pdf_bytes, tmp_path):
    storage = FileStorageService(base_dir=str(tmp_path))

    # Test PNG
    fmt = storage.validate_file_signature(sample_png_bytes, "scan.png")
    assert fmt == "png"

    # Test PDF
    fmt = storage.validate_file_signature(sample_pdf_bytes, "multipage.pdf")
    assert fmt == "pdf"


def test_reject_empty_file(tmp_path):
    storage = FileStorageService(base_dir=str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        storage.validate_file_signature(b"", "empty.png")
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail.lower()


def test_reject_unsupported_extension(sample_png_bytes, tmp_path):
    storage = FileStorageService(base_dir=str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        storage.validate_file_signature(sample_png_bytes, "script.exe")
    assert exc.value.status_code == 400
    assert "unsupported" in exc.value.detail.lower()


def test_reject_mismatched_extension_content(sample_png_bytes, tmp_path):
    storage = FileStorageService(base_dir=str(tmp_path))
    # PNG content with .pdf extension
    with pytest.raises(HTTPException) as exc:
        storage.validate_file_signature(sample_png_bytes, "fake.pdf")
    assert exc.value.status_code == 400


def test_file_cleanup_and_isolation(tmp_path):
    storage = FileStorageService(base_dir=str(tmp_path))
    doc_dir = storage.get_document_dir("doc-test-123")
    doc_dir.mkdir(parents=True, exist_ok=True)
    test_file = doc_dir / "test.txt"
    test_file.write_text("secure data")

    assert doc_dir.exists()
    assert test_file.exists()

    # Delete
    deleted = storage.delete_document("doc-test-123")
    assert deleted is True
    assert not doc_dir.exists()
