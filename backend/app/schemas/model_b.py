from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DiscrepancySeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Flipped negation, changed numbers/dates/names/money
    MATERIAL = "MATERIAL"  # Missing phrases, major word substitutions
    MINOR = "MINOR"        # Harmless punctuation, capitalization of generic words


class DiscrepancyType(str, Enum):
    MISSING_TEXT = "MISSING_TEXT"
    SUBSTITUTED_TEXT = "SUBSTITUTED_TEXT"
    INCORRECT_NUMBER = "INCORRECT_NUMBER"
    INCORRECT_DATE = "INCORRECT_DATE"
    INCORRECT_NAME = "INCORRECT_NAME"
    INCORRECT_NEGATION = "INCORRECT_NEGATION"
    PUNCTUATION_ALTERATION = "PUNCTUATION_ALTERATION"
    UNVERIFIABLE = "UNVERIFIABLE"


class Discrepancy(BaseModel):
    type: DiscrepancyType
    text_segment: str
    expected_segment: str
    severity: DiscrepancySeverity
    evidence: str
    page: int = 1


class VerificationOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    DISCREPANCIES_FOUND = "DISCREPANCIES_FOUND"
    UNVERIFIABLE = "UNVERIFIABLE"


class ModelBResult(BaseModel):
    outcome: VerificationOutcome
    matched_segments: List[str] = Field(default_factory=list)
    missing_segments: List[str] = Field(default_factory=list)
    suspected_substitutions: List[str] = Field(default_factory=list)
    uncertain_segments: List[str] = Field(default_factory=list)
    discrepancies: List[Discrepancy] = Field(default_factory=list)
    agreement_percentage: float = 100.0
    summary_notes: str = ""
    is_mock: bool = False
