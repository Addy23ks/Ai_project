import io
import os
import sys
from pathlib import Path
import pytest
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

# Add backend directory to sys.path so app imports cleanly
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.schemas.ocr import OCRResult, OCRPage, OCRLine, OCRWord
from app.schemas.model_a import ModelAResult, ModelAPage, UncertainSpan, Correction
from app.schemas.model_b import ModelBResult, VerificationOutcome, Discrepancy, DiscrepancyType, DiscrepancySeverity


@pytest.fixture
def sample_png_bytes():
    """Generates a valid test PNG image."""
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Sample Handwritten Note 2024", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_pdf_bytes():
    """Generates a valid 2-page test PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Page 1: Clinical Notes. Eleanor Vance.")
    c.showPage()
    c.drawString(100, 750, "Page 2: Prescriptions. Do NOT give penicillin.")
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def mock_clear_ocr():
    text = "Prescription: Albuterol 90 mcg. Date: 14 Oct 2024. Patient: Eleanor Vance."
    words = [
        OCRWord(text="Prescription:", confidence=98.0),
        OCRWord(text="Albuterol", confidence=95.0),
        OCRWord(text="90", confidence=99.0),
        OCRWord(text="mcg.", confidence=94.0),
        OCRWord(text="Date:", confidence=99.0),
        OCRWord(text="14", confidence=98.0),
        OCRWord(text="Oct", confidence=97.0),
        OCRWord(text="2024.", confidence=99.0),
        OCRWord(text="Patient:", confidence=99.0),
        OCRWord(text="Eleanor", confidence=96.0),
        OCRWord(text="Vance.", confidence=97.0),
    ]
    avg_conf = sum(w.confidence for w in words) / len(words)
    page = OCRPage(
        page_number=1,
        page_text=text,
        words=words,
        word_weighted_confidence=avg_conf
    )
    return OCRResult(
        full_text=text,
        pages=[page],
        word_weighted_confidence=avg_conf,
        total_words=len(words),
        words_with_confidence=len(words)
    )
