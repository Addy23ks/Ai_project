import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Handwritten Document Extraction System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TEMP_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage_temp")
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 20
    MAX_DOCUMENT_PAGES: int = 10
    TEMP_FILE_TTL_HOURS: int = 24

    # Azure AI Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    AZURE_DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None
    AZURE_DOCUMENT_INTELLIGENCE_API_VERSION: str = "2024-11-30"

    # Model A (Transcription Correction)
    MODEL_A_PROVIDER: str = "openai"  # "openai", "azure_openai"
    MODEL_A_ENDPOINT: Optional[str] = None
    MODEL_A_API_KEY: Optional[str] = None
    MODEL_A_DEPLOYMENT: str = "gpt-4o"

    # Model B (Independent Verification)
    MODEL_B_PROVIDER: str = "openai"  # "openai", "azure_openai"
    MODEL_B_ENDPOINT: Optional[str] = None
    MODEL_B_API_KEY: Optional[str] = None
    MODEL_B_DEPLOYMENT: str = "gpt-4o-mini"

    # Scoring weights (sum to 1.0)
    WEIGHT_OCR: float = 0.35
    WEIGHT_VERIFICATION: float = 0.30
    WEIGHT_TEXT_AGREEMENT: float = 0.20
    WEIGHT_COMPLETENESS: float = 0.15

    # Thresholds
    PASS_THRESHOLD: float = 90.0
    REVIEW_THRESHOLD: float = 70.0

    # Fallback to dev simulation if external APIs are not yet configured
    ALLOW_DEV_MOCK_FALLBACK: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
