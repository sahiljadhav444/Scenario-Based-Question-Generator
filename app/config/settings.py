"""
Application Configuration and Environment Settings.
"""
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Dynamically resolve project root and .env path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Pre-load environment variables if .env exists
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Settings
    APP_NAME: str = Field(default="Scenario Question Generator", description="Application name")
    APP_ENV: str = Field(default="development", description="Application environment")
    DEBUG: bool = Field(default=True, description="Debug mode")
    PORT: int = Field(default=8000, description="Server port")
    HOST: str = Field(default="0.0.0.0", description="Server host")

    # API Keys
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, description="OpenRouter API key")
    HUGGINGFACE_API_KEY: Optional[str] = Field(default=None, description="Hugging Face API key/token")

    # Default Models
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default model for Groq provider"
    )
    OPENROUTER_MODEL: str = Field(
        default="meta-llama/llama-3.3-70b-instruct",
        description="Default model for OpenRouter provider"
    )
    HUGGINGFACE_MODEL: str = Field(
        default="meta-llama/Meta-Llama-3-70B-Instruct",
        description="Default model for Hugging Face provider"
    )

    # LLM Provider Fallback Configuration
    LLM_PROVIDER_ORDER: str = Field(
        default="groq,openrouter,huggingface",
        description="Comma-separated fallback order of LLM providers"
    )

    # Generation Parameters
    TEMPERATURE: float = Field(default=0.2, ge=0.0, le=1.0, description="Sampling temperature")
    MAX_TOKENS: int = Field(default=2500, gt=0, description="Max tokens for LLM generation")
    REQUEST_TIMEOUT_SECONDS: int = Field(default=45, gt=0, description="HTTP request timeout in seconds")
    MAX_RETRY_ATTEMPTS: int = Field(default=2, ge=0, description="Max retry attempts for generation or repair")

    @property
    def provider_order_list(self) -> List[str]:
        """Returns the list of provider identifiers in priority order."""
        return [p.strip().lower() for p in self.LLM_PROVIDER_ORDER.split(",") if p.strip()]

    def is_provider_configured(self, provider: str) -> bool:
        """Check if a specific provider has an API key configured."""
        provider = provider.lower()
        if provider == "groq":
            return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())
        elif provider == "openrouter":
            return bool(self.OPENROUTER_API_KEY and self.OPENROUTER_API_KEY.strip())
        elif provider == "huggingface":
            return bool(self.HUGGINGFACE_API_KEY and self.HUGGINGFACE_API_KEY.strip())
        return False

    def get_available_providers(self) -> List[str]:
        """Returns list of providers that have valid API keys present, in priority order."""
        return [p for p in self.provider_order_list if self.is_provider_configured(p)]


# Global settings singleton
settings = Settings()
