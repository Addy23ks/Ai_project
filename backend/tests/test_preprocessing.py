import numpy as np
import cv2
from PIL import Image
from app.services.preprocessing import PreprocessingService


def test_extract_pages_pdf(sample_pdf_bytes, tmp_path):
    preproc = PreprocessingService()
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(sample_pdf_bytes)

    pages = preproc.extract_pages_from_document(pdf_path, tmp_path)
    assert len(pages) == 2
    assert pages[0][0] == 1
    assert pages[1][0] == 2
    assert pages[0][1].exists()
    assert pages[1][1].exists()


def test_extract_pages_png(sample_png_bytes, tmp_path):
    preproc = PreprocessingService()
    png_path = tmp_path / "doc.png"
    png_path.write_bytes(sample_png_bytes)

    pages = preproc.extract_pages_from_document(png_path, tmp_path)
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert pages[0][1].exists()


def test_deskew_and_enhancement(tmp_path):
    preproc = PreprocessingService()

    # Create synthetic test image
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Handwritten Text Note", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (40, 40, 40), 2)
    img_path = tmp_path / "page_1_orig.png"
    cv2.imwrite(str(img_path), img)

    result = preproc.preprocess_page_image(img_path)
    assert result["enhanced_path"].exists()
    assert result["thresh_path"].exists()
    assert result["width"] == 600
    assert result["height"] == 400
