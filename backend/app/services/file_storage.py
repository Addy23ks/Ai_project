import os
import shutil
import uuid
import time
from pathlib import Path
from typing import Tuple, List, Optional
from fastapi import UploadFile, HTTPException

from app.core.config import settings

# Recognized magic numbers
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "tiff": [b"II*\x00", b"MM\x00*"]
}

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


class FileStorageService:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.TEMP_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_document_dir(self, document_id: str) -> Path:
        # Prevent path traversal attacks
        safe_id = Path(document_id).name
        doc_dir = (self.base_dir / safe_id).resolve()
        if not str(doc_dir).startswith(str(self.base_dir)):
            raise HTTPException(status_code=400, detail="Invalid document ID path")
        return doc_dir

    def validate_file_signature(self, content: bytes, filename: str) -> str:
        """Validates file magic bytes and returns the detected format."""
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{ext}'. Supported formats: PDF, PNG, JPG, JPEG, TIFF."
            )

        # Check signatures
        detected_type = None
        for fmt, sigs in MAGIC_SIGNATURES.items():
            for sig in sigs:
                if content.startswith(sig):
                    detected_type = fmt
                    break
            if detected_type:
                break

        if not detected_type:
            raise HTTPException(
                status_code=400,
                detail="File content does not match supported image or PDF signatures. Corrupt or invalid document."
            )

        # Ensure extension matches detected type
        if detected_type == "pdf" and ext != ".pdf":
            raise HTTPException(status_code=400, detail="File extension does not match PDF content.")
        if detected_type in ("jpeg", "png", "tiff") and ext == ".pdf":
            raise HTTPException(status_code=400, detail="File content is an image, not a valid PDF.")

        return detected_type

    async def save_uploaded_file(self, upload_file: UploadFile) -> Tuple[str, str, Path, int]:
        """Validates and saves the uploaded file into an isolated directory."""
        if hasattr(upload_file, "file") and callable(getattr(upload_file.file, "read", None)):
            raw = upload_file.file.read()
            import asyncio
            content = await raw if asyncio.iscoroutine(raw) else raw
        else:
            content = await upload_file.read()
        file_size = len(content)

        if file_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        filename = upload_file.filename or "uploaded_document"
        detected_type = self.validate_file_signature(content, filename)

        document_id = str(uuid.uuid4())
        doc_dir = self.get_document_dir(document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        (doc_dir / "pages").mkdir(exist_ok=True)
        (doc_dir / "artifacts").mkdir(exist_ok=True)

        # Save source file
        source_ext = Path(filename).suffix.lower()
        source_path = doc_dir / f"source{source_ext}"
        with open(source_path, "wb") as f:
            f.write(content)

        return document_id, detected_type, source_path, file_size

    def delete_document(self, document_id: str) -> bool:
        """Deletes all files and directories associated with document_id."""
        doc_dir = self.get_document_dir(document_id)
        if doc_dir.exists():
            shutil.rmtree(doc_dir, ignore_errors=True)
            return True
        return False

    def cleanup_old_files(self) -> int:
        """Cleans up temporary directories older than configured TTL."""
        ttl_seconds = settings.TEMP_FILE_TTL_HOURS * 3600
        now = time.time()
        deleted_count = 0
        if not self.base_dir.exists():
            return 0

        for item in self.base_dir.iterdir():
            if item.is_dir():
                try:
                    mtime = item.stat().st_mtime
                    if now - mtime > ttl_seconds:
                        shutil.rmtree(item, ignore_errors=True)
                        deleted_count += 1
                except Exception:
                    pass
        return deleted_count


storage_service = FileStorageService()
