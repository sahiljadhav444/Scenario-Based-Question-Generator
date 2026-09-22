"""
Tests for LLM Manager Provider Fallback and Routing Logic.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.llm.llm_manager import LLMManager
from app.llm.base_client import BaseLLMClient


class MockClient(BaseLLMClient):
    """Mock client for testing fallback mechanisms."""
    def __init__(self, name: str, default_model: str, available: bool = True, fail: bool = False):
        super().__init__(name=name, default_model=default_model, api_key="dummy_key" if available else None)
        self.fail = fail
        self.generate_called = 0

    async def generate(self, prompt: str, system_prompt=None, model=None, temperature=None, max_tokens=None) -> str:
        self.generate_called += 1
        if self.fail:
            raise RuntimeError(f"Simulated outage on provider '{self.name}'")
        return f'{{"provider": "{self.name}", "status": "success"}}'


def test_llm_manager_primary_success():
    """Test primary provider succeeds without fallback."""
    async def _test():
        manager = LLMManager()
        manager.clients = {
            "groq": MockClient("groq", "llama-3.3-70b-versatile", available=True, fail=False),
            "openrouter": MockClient("openrouter", "meta-llama/llama-3.3-70b-instruct", available=True, fail=False),
        }

        with patch.object(manager, "clients", manager.clients):
            raw, provider, model, duration, fallback = await manager.generate("Test prompt", preferred_provider="groq")

            assert provider == "groq"
            assert fallback is False
            assert manager.clients["groq"].generate_called == 1
            assert manager.clients["openrouter"].generate_called == 0

    asyncio.run(_test())


def test_llm_manager_fallback_to_secondary():
    """Test fallback to secondary when primary provider raises an exception."""
    async def _test():
        manager = LLMManager()
        manager.clients = {
            "groq": MockClient("groq", "llama-3.3-70b-versatile", available=True, fail=True),
            "openrouter": MockClient("openrouter", "meta-llama/llama-3.3-70b-instruct", available=True, fail=False),
            "huggingface": MockClient("huggingface", "meta-llama/Meta-Llama-3-70B-Instruct", available=True, fail=False),
        }

        with patch("app.llm.llm_manager.settings") as mock_settings:
            mock_settings.provider_order_list = ["groq", "openrouter", "huggingface"]
            raw, provider, model, duration, fallback = await manager.generate("Test prompt")

            assert provider == "openrouter"
            assert fallback is True
            assert manager.clients["groq"].generate_called == 1
            assert manager.clients["openrouter"].generate_called == 1
            assert manager.clients["huggingface"].generate_called == 0

    asyncio.run(_test())


def test_llm_manager_all_providers_fail():
    """Test error raised when all configured providers fail."""
    async def _test():
        manager = LLMManager()
        manager.clients = {
            "groq": MockClient("groq", "llama-3.3-70b-versatile", available=True, fail=True),
            "openrouter": MockClient("openrouter", "meta-llama/llama-3.3-70b-instruct", available=True, fail=True),
        }

        with patch("app.llm.llm_manager.settings") as mock_settings:
            mock_settings.provider_order_list = ["groq", "openrouter"]
            with pytest.raises(RuntimeError, match="All available LLM providers"):
                await manager.generate("Test prompt")

    asyncio.run(_test())
