from typing import List
from pydantic import BaseModel, Field


class AlignmentFinding(BaseModel):
    original_span: str
    proposed_span: str
    match_type: str  # "match", "substitution", "insertion", "deletion"
    similarity: float
    is_critical: bool = False


class TextComparisonMetrics(BaseModel):
    char_similarity: float
    word_similarity: float
    insertions: List[str] = Field(default_factory=list)
    deletions: List[str] = Field(default_factory=list)
    substitutions: List[str] = Field(default_factory=list)
    critical_discrepancies: List[str] = Field(default_factory=list)
    normalized_agreement_score: float
    completeness_score: float
