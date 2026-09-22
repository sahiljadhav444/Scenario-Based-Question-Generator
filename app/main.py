"""
Main Application Entrypoint: FastAPI REST API & Interactive CLI.
"""
import sys
import argparse
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, Any

from app.config.settings import settings
from app.models.question_schema import (
    QuestionGenerationResponse,
    TopicRequest,
    ScenarioRequest,
    ScenarioAPIResponse,
    HealthResponse,
)
from app.services.scenario_service import scenario_service
from app.utils.logger import logger

# Conditional FastAPI initialization
try:
    from fastapi import FastAPI, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for application startup and shutdown."""
        logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
        configured_providers = scenario_service.llm_manager.get_configured_providers()
        logger.info(f"Configured LLM providers: {configured_providers}")
        if not configured_providers:
            logger.warning("No LLM API keys configured! Please set keys in .env.")
        yield
        logger.info(f"Shutting down {settings.APP_NAME}")

    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade Topic-to-Scenario Question Generator supporting Groq, OpenRouter, and Hugging Face with fallback.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    FASTAPI_AVAILABLE = True

    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint with basic app information."""
        return {
            "app_name": settings.APP_NAME,
            "version": "1.0.0",
            "docs_url": "/docs",
            "health_check": "/api/v1/health",
            "generate_endpoint": "/api/v1/generate-questions",
        }

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Returns the application health status and list of configured providers."""
        return scenario_service.get_health()

    @app.get("/api/v1/providers", tags=["Providers"])
    async def list_providers() -> Dict[str, Any]:
        """Lists all supported providers and their configuration status."""
        return {
            "fallback_order": settings.provider_order_list,
            "providers": {
                "groq": {
                    "configured": settings.is_provider_configured("groq"),
                    "default_model": settings.GROQ_MODEL,
                },
                "openrouter": {
                    "configured": settings.is_provider_configured("openrouter"),
                    "default_model": settings.OPENROUTER_MODEL,
                },
                "huggingface": {
                    "configured": settings.is_provider_configured("huggingface"),
                    "default_model": settings.HUGGINGFACE_MODEL,
                },
            },
        }

    @app.post(
        "/api/generate-questions",
        response_model=QuestionGenerationResponse,
        status_code=status.HTTP_200_OK,
        tags=["Generation"],
    )
    @app.post(
        "/api/v1/generate-questions",
        response_model=QuestionGenerationResponse,
        status_code=status.HTTP_200_OK,
        tags=["Generation"],
    )
    async def generate_questions(request: TopicRequest) -> QuestionGenerationResponse:
        """
        Generate 5 to 6 scenario-based multiple-choice questions from a user topic.
        First generates a realistic scenario, then creates questions strictly grounded in it.
        Returns ONLY the strict JSON question schema.
        """
        try:
            questions = await scenario_service.generate_pure_questions(request)
            return questions
        except ValueError as val_err:
            logger.error(f"Validation error during generation: {val_err}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(val_err),
            )
        except RuntimeError as run_err:
            logger.error(f"Runtime error during generation: {run_err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(run_err),
            )
        except Exception as exc:
            logger.exception(f"Unexpected error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected internal error occurred: {str(exc)}",
            )

    @app.post(
        "/api/v1/generate-questions-with-metadata",
        response_model=ScenarioAPIResponse,
        status_code=status.HTTP_200_OK,
        tags=["Generation"],
    )
    async def generate_questions_with_metadata(request: TopicRequest) -> ScenarioAPIResponse:
        """
        Generate questions wrapped with execution metadata (latency, provider, attempts).
        """
        try:
            response = await scenario_service.generate_questions_for_topic(request)
            return response
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(val_err),
            )
        except RuntimeError as run_err:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(run_err),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error: {str(exc)}",
            )

except ImportError:
    app = None
    FASTAPI_AVAILABLE = False


# ==========================================
# CLI Execution Handler
# ==========================================

async def run_cli(topic_text: str = None, scenario_text: str = None, provider: str = None):
    """Executes topic scenario and question generation and prints ONLY valid JSON to stdout."""
    if topic_text:
        req = TopicRequest(topic=topic_text, preferred_provider=provider)
    elif scenario_text:
        req = ScenarioRequest(scenario=scenario_text, preferred_provider=provider)
    else:
        sys.stderr.write("Error: Either topic or scenario must be provided.\n")
        sys.exit(1)

    try:
        questions = await scenario_service.generate_pure_questions(req)
        # Print ONLY valid JSON to stdout
        print(json.dumps(questions.model_dump(), indent=2))
    except Exception as e:
        sys.stderr.write(f"Error generating questions: {e}\n")
        sys.exit(1)


def main():
    """Main entrypoint routing to CLI or Uvicorn Server."""
    parser = argparse.ArgumentParser(description="Scenario-Based Question Generator CLI & Backend Server")
    parser.add_argument("--server", action="store_true", help="Start the FastAPI HTTP backend server")
    parser.add_argument("--topic", type=str, help="Topic to generate scenario and questions from")
    parser.add_argument("--scenario", type=str, help="Scenario text to generate questions from (legacy support)")
    parser.add_argument("--provider", type=str, choices=["groq", "openrouter", "huggingface"], help="Preferred LLM provider")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to run server on")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host to run server on")

    args = parser.parse_args()

    if args.topic:
        asyncio.run(run_cli(topic_text=args.topic, provider=args.provider))
    elif args.scenario:
        asyncio.run(run_cli(scenario_text=args.scenario, provider=args.provider))
    elif args.server:
        if not FASTAPI_AVAILABLE:
            sys.stderr.write("[!] FastAPI/Uvicorn not installed. Please run: pip install -r requirements.txt\n")
            return

        try:
            import uvicorn
            uvicorn.run("app.main:app", host=args.host, port=args.port, reload=settings.DEBUG)
        except ImportError:
            sys.stderr.write("[!] Uvicorn is not installed. Please run: pip install -r requirements.txt\n")
    else:
        # If no arguments provided, prompt user for topic interactively and return pure JSON
        try:
            topic_input = input("Enter Topic: ").strip()
            if topic_input:
                asyncio.run(run_cli(topic_text=topic_input, provider=args.provider))
            else:
                parser.print_help()
        except (KeyboardInterrupt, EOFError):
            pass


if __name__ == "__main__":
    main()
