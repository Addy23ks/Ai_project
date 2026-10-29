import math
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np
from PIL import Image, ImageOps
import pypdfium2 as pdfium
from fastapi import HTTPException

from app.core.config import settings


class PreprocessingService:
    def __init__(self):
        pass

    def extract_pages_from_document(
        self, source_path: Path, doc_dir: Path
    ) -> List[Tuple[int, Path]]:
        """
        Extracts each page from the document into a high-resolution PNG image.
        Enforces MAX_DOCUMENT_PAGES.
        """
        pages_dir = doc_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        ext = source_path.suffix.lower()

        page_paths: List[Tuple[int, Path]] = []

        if ext == ".pdf":
            try:
                pdf = pdfium.PdfDocument(str(source_path))
                page_count = len(pdf)

                if page_count == 0:
                    raise HTTPException(status_code=400, detail="The PDF contains no pages.")
                if page_count > settings.MAX_DOCUMENT_PAGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document contains {page_count} pages, which exceeds the limit of {settings.MAX_DOCUMENT_PAGES} pages."
                    )

                for page_idx in range(page_count):
                    page = pdf.get_page(page_idx)
                    # Render at 300 DPI (approx scale 4.167 for standard 72 pt)
                    bitmap = page.render(scale=300 / 72)
                    pil_image = bitmap.to_pil()
                    page_num = page_idx + 1
                    target_path = pages_dir / f"page_{page_num}_orig.png"
                    pil_image.save(target_path, format="PNG")
                    page_paths.append((page_num, target_path))

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process PDF pages: {str(e)}")

        elif ext in (".tiff", ".tif"):
            try:
                with Image.open(source_path) as img:
                    page_idx = 0
                    while True:
                        if page_idx >= settings.MAX_DOCUMENT_PAGES:
                            raise HTTPException(
                                status_code=400,
                                detail=f"TIFF contains too many pages. Limit is {settings.MAX_DOCUMENT_PAGES}."
                            )
                        page_num = page_idx + 1
                        target_path = pages_dir / f"page_{page_num}_orig.png"
                        img.convert("RGB").save(target_path, format="PNG")
                        page_paths.append((page_num, target_path))
                        page_idx += 1
                        try:
                            img.seek(page_idx)
                        except EOFError:
                            break
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process TIFF: {str(e)}")

        else:
            # Single image format (PNG, JPG, etc.)
            try:
                with Image.open(source_path) as img:
                    # Fix EXIF orientation if present
                    img = ImageOps.exif_transpose(img)
                    target_path = pages_dir / "page_1_orig.png"
                    img.convert("RGB").save(target_path, format="PNG")
                    page_paths.append((1, target_path))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read image: {str(e)}")

        return page_paths

    def deskew_image(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Estimates skew angle using minAreaRect on edge/text contours
        and deskews if angle is significant and within [-45, 45].
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        # Invert binary so text is white
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
        )

        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return image, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle

        # Only deskew if noticeably skewed (> 0.5 deg and < 20 deg)
        if abs(angle) > 0.5 and abs(angle) < 25.0:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(
                image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            return deskewed, float(angle)

        return image, 0.0

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Applies CLAHE (Contrast Limited Adaptive Histogram Equalization)
        to gently boost faint handwritten strokes without washing out text.
        """
        if len(image.shape) == 3:
            # Convert to LAB color space to equalize luminance channel only
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            limg = cv2.merge((cl, a_channel, b_channel))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    def denoise_image(self, image: np.ndarray) -> np.ndarray:
        """
        Applies a very conservative bilateral filter to reduce paper grain
        while strictly preserving thin pen strokes, punctuation, and minus signs.
        """
        # Bilateral filter preserves sharp edges (handwriting) while smoothing background
        return cv2.bilateralFilter(image, d=5, sigmaColor=35, sigmaSpace=35)

    def preprocess_page_image(
        self, original_page_path: Path
    ) -> Dict[str, Any]:
        """
        Preprocesses a page image:
        - Keeps original intact
        - Generates deskewed & enhanced representation
        - Generates adaptive threshold representation
        Returns paths and metadata.
        """
        img = cv2.imread(str(original_page_path))
        if img is None:
            raise ValueError(f"Could not load image at {original_page_path}")

        # 1. Deskew
        deskewed_img, skew_angle = self.deskew_image(img)

        # 2. Denoise conservatively
        denoised_img = self.denoise_image(deskewed_img)

        # 3. Enhance contrast
        enhanced_img = self.enhance_contrast(denoised_img)

        # Save enhanced representation
        enhanced_path = original_page_path.parent / (original_page_path.stem.replace("_orig", "") + "_enhanced.png")
        cv2.imwrite(str(enhanced_path), enhanced_img)

        # 4. Optional adaptive threshold representation (for faint pencil / high noise comparison)
        gray = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2GRAY)
        thresh_img = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 12
        )
        thresh_path = original_page_path.parent / (original_page_path.stem.replace("_orig", "") + "_thresh.png")
        cv2.imwrite(str(thresh_path), thresh_img)

        return {
            "original_path": original_page_path,
            "enhanced_path": enhanced_path,
            "thresh_path": thresh_path,
            "skew_angle": round(skew_angle, 2),
            "width": int(img.shape[1]),
            "height": int(img.shape[0])
        }


preprocessing_service = PreprocessingService()
