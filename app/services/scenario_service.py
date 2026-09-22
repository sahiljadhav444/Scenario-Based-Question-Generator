"""
Scenario Service providing business logic and high-level workflow orchestration.
"""
from typing import List, Optional, Union, Tuple
from app.models.question_schema import (
    QuestionGenerationResponse,
    TopicRequest,
    ScenarioRequest,
    ScenarioAPIResponse,
    HealthResponse,
)
from app.services.question_generator import QuestionGenerator, question_generator as default_generator
from app.llm.llm_manager import LLMManager, llm_manager as default_llm_manager
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger("ScenarioService")


class ScenarioService:
    """High-level service interface for topic-based and scenario-based question generation."""

    def __init__(
        self,
        generator: Optional[QuestionGenerator] = None,
        llm_mgr: Optional[LLMManager] = None,
    ):
        self.generator = generator or default_generator
        self.llm_manager = llm_mgr or default_llm_manager

    def get_health(self) -> HealthResponse:
        """Returns the system health and list of active LLM providers."""
        available = self.llm_manager.get_configured_providers()
        return HealthResponse(
            status="healthy" if available else "degraded (no API keys configured)",
            version="1.0.0",
            available_providers=available,
        )

    async def generate_scenario_from_topic(
        self,
        topic: str,
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Tuple[str, str, str, float, bool]:
        """Generates a realistic scenario based on a topic."""
        return await self.generator.generate_scenario_from_topic(
            topic=topic,
            preferred_provider=preferred_provider,
            model=model,
            temperature=temperature,
        )

    async def generate_pure_questions(
        self, request: Union[TopicRequest, ScenarioRequest]
    ) -> QuestionGenerationResponse:
        """
        Generates questions from topic/scenario and returns strictly the pure QuestionGenerationResponse.
        """
        logger.info("Generating pure questions JSON")
        questions, _ = await self.generator.generate_questions(request)
        return questions

    async def generate_questions_for_topic(
        self, request: Union[TopicRequest, ScenarioRequest]
    ) -> ScenarioAPIResponse:
        """
        Generates scenario and questions from topic with metadata envelope.
        """
        logger.info("Processing topic generation request")
        questions, metadata = await self.generator.generate_questions(request)

        return ScenarioAPIResponse(
            success=True,
            message="Successfully generated valid scenario-based questions.",
            data=questions,
            metadata=metadata,
        )

    async def generate_questions_for_scenario(
        self, request: Union[TopicRequest, ScenarioRequest]
    ) -> ScenarioAPIResponse:
        """
        Coordinates the question generation workflow with metadata envelope (backward compatibility alias).
        """
        return await self.generate_questions_for_topic(request)


# Global scenario service instance
scenario_service = ScenarioService()

