"""
Hugging Face LLM Client Implementation.
"""
from typing import Optional
import httpx
from app.llm.base_client import BaseLLMClient
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger("HuggingFaceClient")


class HuggingFaceClient(BaseLLMClient):
    """Client for Hugging Face Inference Endpoints / Serverless API."""

    BASE_CHAT_URL = "https://api-inference.huggingface.co/v1/chat/completions"
    BASE_MODELS_URL = "https://api-inference.huggingface.co/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        super().__init__(
            name="huggingface",
            default_model=default_model or settings.HUGGINGFACE_MODEL,
            api_key=api_key or settings.HUGGINGFACE_API_KEY,
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
            raise ValueError("Hugging Face API key is not configured. Set HUGGINGFACE_API_KEY in .env.")

        target_model = model or self.default_model
        target_temp = max(temperature if temperature is not None else settings.TEMPERATURE, 0.01)
        target_max_tokens = max_tokens or settings.MAX_TOKENS

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # First attempt: OpenAI-compatible router endpoint
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": target_temp,
            "max_tokens": target_max_tokens,
        }

        logger.debug(f"Sending request to Hugging Face API (model={target_model})")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(self.BASE_CHAT_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"Hugging Face chat endpoint error: {e}. Trying direct model URL...")

            # Fallback to direct model inference endpoint
            model_url = f"{self.BASE_MODELS_URL}/{target_model}"
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            direct_payload = {
                "inputs": full_prompt,
                "parameters": {
                    "temperature": target_temp,
                    "max_new_tokens": target_max_tokens,
                    "return_full_text": False,
                },
            }
            response = await client.post(model_url, json=direct_payload, headers=headers)

            if response.status_code != 200:
                error_body = response.text
                logger.error(f"Hugging Face API error ({response.status_code}): {error_body}")
                response.raise_for_status()

            data = response.json()
            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                return data[0]["generated_text"]
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"]
            else:
                return str(data)
