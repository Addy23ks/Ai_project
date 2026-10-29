import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class VisionLLMAdapter:
    """
    Adapter for vision-capable LLMs (OpenAI, Azure OpenAI, or compatible endpoints).
    """
    def __init__(
        self,
        provider: str,
        api_key: Optional[str],
        endpoint: Optional[str] = None,
        deployment_or_model: str = "gpt-4o"
    ):
        self.provider = (provider or "openai").lower()
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = deployment_or_model

    @property
    def is_configured(self) -> bool:
        if not self.api_key or self.api_key.startswith("your-") or "placeholder" in self.api_key:
            return False
        return True

    def _encode_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def call_vision_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        image_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Sends system + user prompt with image to the configured vision LLM and expects JSON.
        """
        if not self.is_configured:
            raise ValueError(f"Provider {self.provider} API key is not configured.")

        # Determine target URL and headers
        if self.provider == "azure_openai":
            if not self.endpoint:
                raise ValueError("Azure OpenAI endpoint is required when using azure_openai provider.")
            clean_endpoint = self.endpoint.rstrip("/")
            url = f"{clean_endpoint}/openai/deployments/{self.model}/chat/completions?api-version=2024-02-15-preview"
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
        else:
            # Standard OpenAI or OpenAI-compatible (LiteLLM, etc.)
            base_url = self.endpoint.rstrip("/") if self.endpoint else "https://api.openai.com/v1"
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

        # Build message payload
        user_content: list = [{"type": "text", "text": user_prompt}]
        if image_path and image_path.exists():
            b64_img = self._encode_image(image_path)
            mime_type = "image/png"
            if image_path.suffix.lower() in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{b64_img}",
                    "detail": "high"
                }
            })

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    logger.error(f"Vision LLM request failed with status code {res.status_code}")
                    raise RuntimeError(f"Vision LLM error ({res.status_code}): {res.text[:200]}")

                data = res.json()
                raw_content = data["choices"][0]["message"]["content"]
                return json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {str(e)}")
                raise ValueError(f"Vision LLM did not return valid JSON: {str(e)}")
            except Exception as e:
                logger.error(f"Error invoking Vision LLM ({self.provider}): {str(e)}")
                raise
