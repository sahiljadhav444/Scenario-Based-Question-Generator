"""
Groq LLM Client Implementation.
"""
from typing import Optional
import httpx
from app.llm.base_client import BaseLLMClient
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger("GroqClient")


class GroqClient(BaseLLMClient):
    """Client for Groq fast inference API."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        super().__init__(
            name="groq",
            default_model=default_model or settings.GROQ_MODEL,
            api_key=api_key or settings.GROQ_API_KEY,
        )
        self.timeout = timeout_seconds or settings.REQUEST_TIMEOUT_SECONDS

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.is_available():
            raise ValueError("Groq API key is not configured. Set GROQ_API_KEY in .env.")

        target_model = model or self.default_model
        target_temp = temperature if temperature is not None else settings.TEMPERATURE
        target_max_tokens = max_tokens or settings.MAX_TOKENS

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": target_temp,
            "max_tokens": target_max_tokens,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Sending request to Groq API (model={target_model})")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.BASE_URL, json=payload, headers=headers)

            if response.status_code != 200:
                error_body = response.text
                logger.error(f"Groq API error ({response.status_code}): {error_body}")
                response.raise_for_status()

            data = response.json()
            try:
                content = data["choices"][0]["message"]["content"]
                return content
            except (KeyError, IndexError) as exc:
                raise ValueError(f"Unexpected response structure from Groq: {data}") from exc
