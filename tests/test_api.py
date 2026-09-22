"""
Tests for FastAPI Endpoints and Schema Serialization.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app, FASTAPI_AVAILABLE
from tests.test_json_validator import VALID_5_QUESTIONS_PAYLOAD


@pytest.fixture
def client():
    """Fixture to create a FastAPI test client."""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not installed")
    return TestClient(app)


def test_health_endpoint(client):
    """Test the /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "status" in data
    assert "available_providers" in data


def test_root_endpoint(client):
    """Test the root / endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "generate_endpoint" in data


def test_generate_questions_endpoint(client):
    """Test generating pure questions JSON endpoint with topic."""
    with patch("app.services.question_generator.QuestionGenerator.generate_questions") as mock_generate:
        from app.models.question_schema import QuestionGenerationResponse, GenerationMetadata

        model_resp = QuestionGenerationResponse.model_validate(VALID_5_QUESTIONS_PAYLOAD)
        mock_meta = GenerationMetadata(
            provider_used="groq",
            model_used="llama-3.3-70b-versatile",
            duration_seconds=0.5,
            total_questions=5,
            attempts=1,
            fallback_occurred=False,
        )
        mock_generate.return_value = (model_resp, mock_meta)

        payload = {
            "topic": "Human Resources"
        }
        response = client.post("/api/v1/generate-questions", json=payload)
        assert response.status_code == 200
        data = response.json()

        # Check required field names
        assert "topic" in data
        assert "scenario" in data
        assert "questions" in data
        assert len(data["questions"]) == 5

        first_q = data["questions"][0]
        assert "questionId" in first_q
        assert "questionType" in first_q
        assert "difficultyTag" in first_q
        assert "subject" in first_q
        assert "questionText" in first_q
        assert "optionsList" in first_q

        assert len(first_q["optionsList"]) == 4
        first_opt = first_q["optionsList"][0]
        assert "optionSequenceNo" in first_opt
        assert "optionText" in first_opt
        assert "isCorrect" in first_opt


def test_generate_questions_with_metadata_endpoint(client):
    """Test generating questions with metadata envelope."""
    with patch("app.services.question_generator.QuestionGenerator.generate_questions") as mock_generate:
        from app.models.question_schema import QuestionGenerationResponse, GenerationMetadata

        model_resp = QuestionGenerationResponse.model_validate(VALID_5_QUESTIONS_PAYLOAD)
        mock_meta = GenerationMetadata(
            provider_used="groq",
            model_used="llama-3.3-70b-versatile",
            duration_seconds=0.75,
            total_questions=5,
            attempts=1,
            fallback_occurred=False,
        )
        mock_generate.return_value = (model_resp, mock_meta)

        payload = {
            "topic": "Human Resources"
        }
        response = client.post("/api/v1/generate-questions-with-metadata", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        assert data["data"]["topic"] == "Human Resources"
        assert data["metadata"]["provider_used"] == "groq"
        assert len(data["data"]["questions"]) == 5


def test_invalid_topic_validation_error(client):
    """Test that missing or too short topic returns 422 Unprocessable Entity."""
    response = client.post("/api/v1/generate-questions", json={"topic": ""})
    assert response.status_code == 422

