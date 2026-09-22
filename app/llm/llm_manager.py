"""
LLM Manager for Multi-Provider Orchestration, Routing, and Automatic Fallback.
"""
import time
from typing import Dict, List, Optional, Tuple
from app.llm.base_client import BaseLLMClient
from app.llm.groq_client import GroqClient
from app.llm.openrouter_client import OpenRouterClient
from app.llm.huggingface_client import HuggingFaceClient
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger("LLMManager")


class LLMManager:
    """
    Orchestrates LLM providers with automatic fallback, load balancing,
    and timeout handling.
    """

    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {
            "groq": GroqClient(),
            "openrouter": OpenRouterClient(),
            "huggingface": HuggingFaceClient(),
        }

    def get_client(self, provider: str) -> Optional[BaseLLMClient]:
        """Returns the client for the specified provider name."""
        return self.clients.get(provider.lower())

    def get_configured_providers(self) -> List[str]:
        """Returns list of provider names that are configured with API keys."""
        return [name for name, client in self.clients.items() if client.is_available()]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, str, str, float, bool]:
        """
        Generates text by querying LLM providers with automatic fallback.

        Returns:
            Tuple of:
            - raw_response (str)
            - provider_name_used (str)
            - model_name_used (str)
            - duration_seconds (float)
            - fallback_occurred (bool)
        """
        # Determine candidate providers
        candidates: List[str] = []

        if preferred_provider:
            pref = preferred_provider.lower().strip()
            if pref in self.clients and self.clients[pref].is_available():
                candidates.append(pref)
            else:
                logger.warning(
                    f"Preferred provider '{preferred_provider}' is not available or configured. "
                    f"Falling back to default provider order."
                )

        # Append configured providers in configured order
        for p in settings.provider_order_list:
            if p in self.clients and self.clients[p].is_available() and p not in candidates:
                candidates.append(p)

        if not candidates:
            available_clients = [c for c, client in self.clients.items() if client.is_available()]
            raise RuntimeError(
                "No LLM provider is available or configured with valid API keys. "
                f"Configured keys: {available_clients}. "
                "Please configure at least one of: GROQ_API_KEY, OPENROUTER_API_KEY, or HUGGINGFACE_API_KEY in .env."
            )

        start_time = time.perf_counter()
        last_error = None
        fallback_occurred = False

        for index, provider_name in enumerate(candidates):
            client = self.clients[provider_name]
            target_model = model if (model and index == 0) else client.default_model

            if index > 0:
                fallback_occurred = True
                logger.info(f"Failing over to provider: {provider_name} (model: {target_model})")

            try:
                logger.info(f"Attempting generation via provider: {provider_name} (model: {target_model})")
                raw_response = await client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=target_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                duration = time.perf_counter() - start_time
                logger.info(f"Successfully generated response from {provider_name} in {duration:.2f}s")
                return raw_response, provider_name, target_model, duration, fallback_occurred

            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Provider '{provider_name}' failed with error: {str(exc)}. "
                    f"Checking next available provider..."
                )
                continue

        # If all candidates failed
        duration = time.perf_counter() - start_time
        raise RuntimeError(
            f"All available LLM providers ({candidates}) failed to generate a response. "
            f"Last error: {last_error}"
        )


# Global singleton instance
llm_manager = LLMManager()
