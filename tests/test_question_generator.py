"""
Tests for QuestionGenerator service.
"""
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.question_generator import QuestionGenerator
from app.models.question_schema import TopicRequest, ScenarioRequest
from tests.test_json_validator import VALID_5_QUESTIONS_PAYLOAD


def test_topic_question_generation_success():
    """Test successful scenario and question generation from a topic."""
    async def _test():
        mock_llm_manager = MagicMock()
        # 1st call: generate scenario from topic
        # 2nd call: generate questions from generated scenario
        generated_scenario = "A college introduces an online library system where students borrow and return books."
        mock_llm_manager.generate = AsyncMock(
            side_effect=[
                (generated_scenario, "groq", "llama-3.3-70b-versatile", 0.45, False),
                (json.dumps(VALID_5_QUESTIONS_PAYLOAD), "groq", "llama-3.3-70b-versatile", 0.85, False),
            ]
        )

        generator = QuestionGenerator(manager=mock_llm_manager)
        req = TopicRequest(topic="Library Management System")

        response, metadata = await generator.generate_questions(req)

        assert len(response.questions) == 5
        assert response.topic == "Library Management System"
        assert response.questions[0].questionId == "11111111-1111-4111-8111-111111111111"
        assert response.questions[0].questionType == "scenario_based"
        assert response.questions[0].difficultyTag == "Easy"
        assert response.questions[0].optionsList[1].isCorrect is True
        assert metadata.provider_used == "groq"
        assert metadata.fallback_occurred is False
        assert metadata.total_questions == 5
        assert mock_llm_manager.generate.call_count == 2

    asyncio.run(_test())


def test_generate_scenario_from_topic_direct():
    """Test generating scenario text directly from topic."""
    async def _test():
        mock_llm_manager = MagicMock()
        mock_llm_manager.generate = AsyncMock(
            return_value=(
                "Scenario: A customer orders groceries online and selects a 2-hour delivery window.",
                "groq",
                "llama-3.3-70b-versatile",
                0.35,
                False,
            )
        )
        generator = QuestionGenerator(manager=mock_llm_manager)
        scenario, provider, model, dur, fallback = await generator.generate_scenario_from_topic("Online Grocery")

        assert "A customer orders groceries online" in scenario
        assert not scenario.startswith("Scenario:")
        assert provider == "groq"

    asyncio.run(_test())


def test_question_generation_auto_repair():
    """Test self-repair workflow when the question generation attempt has invalid JSON syntax."""
    async def _test():
        generated_scenario = "A hospital manages emergency patient appointments and bed allocations."
        invalid_raw = "Here is bad json: { 'questions': [ incomplete "
        valid_raw = json.dumps(VALID_5_QUESTIONS_PAYLOAD)

        mock_llm_manager = MagicMock()
        # 1st call: scenario generation
        # 2nd call: question generation returns invalid JSON
        # 3rd call: auto-repair returns valid JSON
        mock_llm_manager.generate = AsyncMock(
            side_effect=[
                (generated_scenario, "groq", "llama-3.3-70b-versatile", 0.3, False),
                (invalid_raw, "groq", "llama-3.3-70b-versatile", 0.4, False),
                (valid_raw, "groq", "llama-3.3-70b-versatile", 0.6, False),
            ]
        )

        generator = QuestionGenerator(manager=mock_llm_manager)
        req = TopicRequest(topic="Hospital Management")

        response, metadata = await generator.generate_questions(req)

        assert len(response.questions) == 5
        assert metadata.attempts == 2
        assert mock_llm_manager.generate.call_count == 3

    asyncio.run(_test())


def test_legacy_scenario_request_support():
    """Test backward compatibility when ScenarioRequest with scenario is provided."""
    async def _test():
        mock_llm_manager = MagicMock()
        mock_llm_manager.generate = AsyncMock(
            return_value=(
                json.dumps(VALID_5_QUESTIONS_PAYLOAD),
                "groq",
                "llama-3.3-70b-versatile",
                0.85,
                False,
            )
        )

        generator = QuestionGenerator(manager=mock_llm_manager)
        req = ScenarioRequest(
            scenario="A company wants to identify employees who earn more than $50,000 and work in the Sales department."
        )

        response, metadata = await generator.generate_questions(req)

        assert len(response.questions) == 5
        assert response.scenario == req.scenario
        assert mock_llm_manager.generate.call_count == 1

    asyncio.run(_test())

