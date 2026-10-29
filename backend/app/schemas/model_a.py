from typing import List, Optional
from pydantic import BaseModel, Field


class UncertainSpan(BaseModel):
    text: str
    page: int = 1
    location: str = "middle"
    reason: str = "ambiguous handwriting stroke"


class Correction(BaseModel):
    original_ocr: str
    corrected: str
    reason: str
    evidence: str
    page: int = 1


class ModelAPage(BaseModel):
    page_number: int
    text: str


class ModelAResult(BaseModel):
    proposed_transcription: str
    pages: List[ModelAPage] = Field(default_factory=list)
    uncertain_spans: List[UncertainSpan] = Field(default_factory=list)
    corrections_made: List[Correction] = Field(default_factory=list)
    is_mock: bool = False
    raw_response: Optional[str] = None
