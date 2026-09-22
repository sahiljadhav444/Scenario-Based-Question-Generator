"""
Question Generator Service orchestrating prompts, LLM invocations, validation, and auto-repair.
"""
from typing import Optional, Tuple, Union
from app.prompts.scenario_question_prompt import (
    TOPIC_SCENARIO_SYSTEM_PROMPT,
    format_topic_scenario_prompt,
    SCENARIO_QUESTION_SYSTEM_PROMPT,
    format_scenario_prompt,
    format_repair_prompt,
)
from app.llm.llm_manager import LLMManager, llm_manager as default_llm_manager
from app.services.json_validator import JSONValidator, json_validator as default_validator
from app.models.question_schema import (
    QuestionGenerationResponse,
    GenerationMetadata,
    TopicRequest,
    ScenarioRequest,
)
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger("QuestionGenerator")


class QuestionGenerator:
    """
    Coordinates prompt construction, multi-provider LLM execution,
    strict schema validation, and automatic retry/repair.
    """

    def __init__(
        self,
        manager: Optional[LLMManager] = None,
        validator: Optional[JSONValidator] = None,
    ):
        self.llm_manager = manager or default_llm_manager
        self.validator = validator or default_validator

    async def generate_scenario_from_topic(
        self,
        topic: str,
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Tuple[str, str, str, float, bool]:
        """
        Generates a realistic, focused scenario directly related to the given topic.

        Returns:
            Tuple of (scenario_text, provider_used, model_used, duration_seconds, fallback_occurred)
        """
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty or whitespace.")

        cleaned_topic = topic.strip()
        logger.info(f"Generating scenario for topic: '{cleaned_topic}'")

        prompt = format_topic_scenario_prompt(cleaned_topic)

        (
            raw_output,
            provider_used,
            model_used,
            duration,
            fallback_flag,
        ) = await self.llm_manager.generate(
            prompt=prompt,
            system_prompt=TOPIC_SCENARIO_SYSTEM_PROMPT,
            preferred_provider=preferred_provider,
            model=model,
            temperature=temperature,
        )

        scenario_text = self.validator.validate_generated_scenario(raw_output)
        logger.info(f"Generated scenario ({len(scenario_text)} chars) for topic '{cleaned_topic}'")
        return scenario_text, provider_used, model_used, duration, fallback_flag

    async def generate_questions_from_scenario(
        self,
        scenario: str,
        topic: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Tuple[QuestionGenerationResponse, GenerationMetadata]:
        """
        Generates 5-6 scenario-based questions grounded strictly in the given scenario.

        Args:
            scenario: Ground-truth scenario text.
            topic: Optional topic string associated with the scenario.

        Returns:
            Tuple of (QuestionGenerationResponse, GenerationMetadata)
        """
        if not scenario or not scenario.strip():
            raise ValueError("Scenario cannot be empty.")

        cleaned_scenario = scenario.strip()
        t_val = (topic or "Scenario Assessment").strip()
        logger.info(f"Generating questions from scenario (length: {len(cleaned_scenario)} chars)")

        user_prompt = format_scenario_prompt(cleaned_scenario, topic=t_val)

        attempts = 0
        max_attempts = settings.MAX_RETRY_ATTEMPTS + 1
        last_error = None
        raw_output = ""
        provider_used = "unknown"
        model_used = "unknown"
        total_duration = 0.0
        fallback_occurred = False

        current_prompt = user_prompt

        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Question generation attempt {attempts}/{max_attempts}")

            try:
                (
                    raw_output,
                    provider_used,
                    model_used,
                    duration,
                    fallback_flag,
                ) = await self.llm_manager.generate(
                    prompt=current_prompt,
                    system_prompt=SCENARIO_QUESTION_SYSTEM_PROMPT,
                    preferred_provider=preferred_provider,
                    model=model,
                    temperature=temperature,
                )
                total_duration += duration
                if fallback_flag:
                    fallback_occurred = True

                # Validate the generated JSON response
                validated_response, _ = self.validator.validate_raw_response(
                    raw_output,
                    fallback_scenario=cleaned_scenario,
                    topic=t_val,
                )

                metadata = GenerationMetadata(
                    provider_used=provider_used,
                    model_used=model_used,
                    duration_seconds=round(total_duration, 3),
                    total_questions=len(validated_response.questions),
                    attempts=attempts,
                    fallback_occurred=fallback_occurred,
                )

                logger.info(
                    f"Successfully generated {len(validated_response.questions)} questions "
                    f"using {provider_used} in {total_duration:.2f}s"
                )
                return validated_response, metadata

            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Attempt {attempts} failed validation/generation with error: {str(exc)}"
                )

                if attempts < max_attempts:
                    logger.info("Attempting automated self-repair prompt...")
                    current_prompt = format_repair_prompt(
                        scenario=cleaned_scenario,
                        raw_output=raw_output,
                        error_message=str(exc),
                        topic=t_val,
                    )

        raise RuntimeError(
            f"Failed to generate valid scenario questions after {max_attempts} attempts. "
            f"Last validation error: {last_error}"
        )

    async def generate_questions(
        self,
        request: Union[TopicRequest, ScenarioRequest],
    ) -> Tuple[QuestionGenerationResponse, GenerationMetadata]:
        """
        Orchestrates full generation pipeline:
        1. Topic validation (or scenario fallback).
        2. Scenario generation from topic (if topic provided and scenario omitted).
        3. Generated scenario validation.
        4. Question generation from scenario (5-6 questions).
        5. JSON validation & output envelope.

        Args:
            request: TopicRequest or ScenarioRequest containing parameters.

        Returns:
            Tuple of (QuestionGenerationResponse, GenerationMetadata)
        """
        # Case 1: Topic is provided
        if getattr(request, "topic", None) and request.topic and request.topic.strip():
            topic = request.topic.strip()
            # If scenario was not explicitly passed, generate it from topic
            if not getattr(request, "scenario", None) or not request.scenario or not request.scenario.strip():
                (
                    scenario,
                    sc_provider,
                    sc_model,
                    sc_duration,
                    sc_fallback,
                ) = await self.generate_scenario_from_topic(
                    topic=topic,
                    preferred_provider=request.preferred_provider,
                    model=request.model,
                    temperature=request.temperature,
                )
            else:
                scenario = self.validator.validate_generated_scenario(request.scenario)
                sc_provider, sc_model, sc_duration, sc_fallback = "direct", "direct", 0.0, False

            response, metadata = await self.generate_questions_from_scenario(
                scenario=scenario,
                topic=topic,
                preferred_provider=request.preferred_provider,
                model=request.model,
                temperature=request.temperature,
            )

            # Combine metadata duration and fallbacks
            total_duration = round(metadata.duration_seconds + sc_duration, 3)
            combined_metadata = GenerationMetadata(
                provider_used=metadata.provider_used if metadata.provider_used != "unknown" else sc_provider,
                model_used=metadata.model_used if metadata.model_used != "unknown" else sc_model,
                duration_seconds=total_duration,
                total_questions=metadata.total_questions,
                attempts=metadata.attempts,
                fallback_occurred=metadata.fallback_occurred or sc_fallback,
            )
            return response, combined_metadata

        # Case 2: Scenario is provided directly (legacy / backward compatibility)
        elif getattr(request, "scenario", None) and request.scenario and request.scenario.strip():
            scenario = self.validator.validate_generated_scenario(request.scenario)
            return await self.generate_questions_from_scenario(
                scenario=scenario,
                topic="Scenario Assessment",
                preferred_provider=request.preferred_provider,
                model=request.model,
                temperature=request.temperature,
            )

        raise ValueError("Invalid request: either 'topic' or 'scenario' must be provided.")


# Global service instance
question_generator = QuestionGenerator()
