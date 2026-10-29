from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class OCRWord(BaseModel):
    text: str
    confidence: Optional[float] = None
    polygon: Optional[List[float]] = None
    span: Optional[Tuple[int, int]] = None


class OCRLine(BaseModel):
    text: str
    confidence: Optional[float] = None
    words: List[OCRWord] = Field(default_factory=list)
    polygon: Optional[List[float]] = None


class OCRPage(BaseModel):
    page_number: int
    width: float = 0.0
    height: float = 0.0
    unit: str = "pixel"
    lines: List[OCRLine] = Field(default_factory=list)
    words: List[OCRWord] = Field(default_factory=list)
    page_text: str = ""
    word_weighted_confidence: float = 0.0
    is_handwritten: bool = True


class OCRResult(BaseModel):
    full_text: str = ""
    pages: List[OCRPage] = Field(default_factory=list)
    word_weighted_confidence: float = 0.0
    total_words: int = 0
    words_with_confidence: int = 0
    missing_confidence_count: int = 0
    is_mock: bool = False
    warnings: List[str] = Field(default_factory=list)
