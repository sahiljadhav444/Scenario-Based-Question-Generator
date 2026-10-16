"""
Pydantic Schemas and Data Models for Scenario Question Generation.
"""
import uuid
import re
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Option(BaseModel):
    """Represents a single answer option for a multiple-choice question."""
    optionSequenceNo: int = Field(
        ...,
        ge=1,
        le=4,
        description="Sequence number of the option (1, 2, 3, or 4)"
    )
    optionText: str = Field(
        ...,
        min_length=1,
        description="Text content of the option"
    )
    isCorrect: bool = Field(
        ...,
        description="Boolean indicating whether this option is the correct answer"
    )

    @field_validator("optionText")
    @classmethod
    def validate_option_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Option text cannot be empty or whitespace only.")
        
        # Disallow generic non-informative options
        forbidden_patterns = [
            r"^all of the above\.?$",
            r"^none of the above\.?$",
            r"^both [a-d] and [a-d]\.?$",
            r"^neither [a-d] nor [a-d]\.?$",
        ]
        for pattern in forbidden_patterns:
            if re.match(pattern, trimmed, re.IGNORECASE):
                raise ValueError(
                    f"Option text '{trimmed}' is prohibited. Generic options like 'All/None of the above' are not allowed."
                )

        return trimmed


class ScenarioItem(BaseModel):
    """Represents a single scenario generated from a topic."""
    scenarioId: str = Field(
        ...,
        description="Unique UUID identifier for the scenario"
    )
    scenarioText: str = Field(
        ...,
        min_length=15,
        description="A relevant scenario generated from the topic"
    )

    @field_validator("scenarioId")
    @classmethod
    def validate_scenario_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Scenario ID cannot be empty.")
        try:
            val_uuid = uuid.UUID(trimmed)
            return str(val_uuid)
        except ValueError:
            raise ValueError(f"scenarioId must be a valid UUID string. Received: '{v}'")

    @field_validator("scenarioText")
    @classmethod
    def validate_scenario_text(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 15:
            raise ValueError(f"Scenario text is too short ({len(trimmed)} chars).")
        return trimmed


class Question(BaseModel):
    """Represents a single scenario-based multiple-choice or multiple-select question."""
    model_config = ConfigDict(extra="ignore")

    questionId: str = Field(
        ...,
        description="Unique UUID identifier for the question"
    )
    questionType: str = Field(
        default="scenario_based",
        description="Type of the question, must be exactly 'scenario_based'"
    )
    questionFormat: Literal["MCQ", "MSQ"] = Field(
        default="MCQ",
        description="Format of the question: 'MCQ' (single correct) or 'MSQ' (multiple correct)"
    )
    difficultyTag: Literal["Easy", "Medium", "Hard"] = Field(
        ...,
        description="Difficulty level of the question ('Easy', 'Medium', or 'Hard')"
    )
    subject: Optional[str] = Field(
        default="Scenario Assessment",
        description="Subject area identified based on the scenario"
    )
    questionText: str = Field(
        ...,
        min_length=5,
        description="The scenario question text"
    )
    optionsList: List[Option] = Field(
        ...,
        description="List of exactly 4 options"
    )

    @field_validator("questionId")
    @classmethod
    def validate_question_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Question ID cannot be empty.")
        try:
            val_uuid = uuid.UUID(trimmed)
            return str(val_uuid)
        except ValueError:
            raise ValueError(f"questionId must be a valid UUID string. Received: '{v}'")

    @field_validator("questionType")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        trimmed = v.strip()
        if trimmed != "scenario_based":
            raise ValueError(f"questionType must be exactly 'scenario_based'. Received: '{v}'")
        return trimmed

    @field_validator("difficultyTag")
    @classmethod
    def validate_difficulty_tag(cls, v: str) -> str:
        if v not in ("Easy", "Medium", "Hard"):
            raise ValueError(f"difficultyTag must be 'Easy', 'Medium', or 'Hard'. Received: '{v}'")
        return v

    @field_validator("questionText")
    @classmethod
    def validate_question_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Question text cannot be empty.")
        return trimmed

    @field_validator("optionsList")
    @classmethod
    def validate_options_list(cls, v: List[Option]) -> List[Option]:
        if len(v) != 4:
            raise ValueError(f"Every question must contain exactly 4 options in optionsList. Found: {len(v)}")

        # Check sequence numbers
        seq_nos = [opt.optionSequenceNo for opt in v]
        if sorted(seq_nos) != [1, 2, 3, 4]:
            raise ValueError(f"optionSequenceNo values must be exactly 1, 2, 3, and 4. Found: {seq_nos}")

        # Check at least one correct option
        correct_count = sum(1 for opt in v if opt.isCorrect is True)
        if correct_count == 0:
            raise ValueError("Exactly ONE option must have isCorrect: true. Found: 0")

        # Check for duplicate options (case-insensitive)
        seen_texts = set()
        for opt in v:
            normalized = opt.optionText.lower().strip()
            if normalized in seen_texts:
                raise ValueError(f"Duplicate option found within question: '{opt.optionText}'")
            seen_texts.add(normalized)

        return v

    @model_validator(mode="after")
    def validate_mcq_msq_correctness(self) -> "Question":
        correct_count = sum(1 for opt in self.optionsList if opt.isCorrect is True)
        if self.questionFormat == "MCQ":
            if correct_count != 1:
                raise ValueError(
                    f"Exactly ONE option must have isCorrect: true for MCQ questions. Found: {correct_count}"
                )
        elif self.questionFormat == "MSQ":
            if correct_count < 2:
                raise ValueError(
                    f"At least TWO options must have isCorrect: true for MSQ questions. Found: {correct_count}"
                )
        return self


class QuestionGenerationResponse(BaseModel):
    """Schema for the strict JSON output structure expected from topic/scenario question generation."""
    topic: str = Field(
        ...,
        min_length=1,
        description="The topic for which scenarios and questions were generated"
    )
    scenarios: List[ScenarioItem] = Field(
        default_factory=list,
        description="List of 2 to 3 generated scenarios based on the topic"
    )
    scenario: Optional[str] = Field(
        default=None,
        description="Legacy scenario text for backward compatibility"
    )
    questions: List[Question] = Field(
        ...,
        description="List of 5 to 6 scenario-based questions across all generated scenarios"
    )

    @field_validator("topic")
    @classmethod
    def validate_topic_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Topic text cannot be empty.")
        return trimmed

    @model_validator(mode="after")
    def validate_scenarios_and_questions(self) -> "QuestionGenerationResponse":
        # Check questions count
        if not (5 <= len(self.questions) <= 6):
            raise ValueError(
                f"Generated questions count must be between 5 and 6. Received: {len(self.questions)}"
            )

        # Check unique questionIds
        seen_qids = set()
        for q in self.questions:
            q_id = q.questionId.strip().lower()
            if q_id in seen_qids:
                raise ValueError(f"Duplicate questionId detected: '{q.questionId}'")
            seen_qids.add(q_id)

        # Validate difficulty distribution
        counts = {"Easy": 0, "Medium": 0, "Hard": 0}
        for q in self.questions:
            counts[q.difficultyTag] = counts.get(q.difficultyTag, 0) + 1

        total = len(self.questions)
        if total == 5:
            if counts["Easy"] < 1:
                raise ValueError(f"For 5 questions, at least 1 Easy question is required. Found: {counts['Easy']}")
            if counts["Medium"] < 2:
                raise ValueError(f"For 5 questions, at least 2 Medium questions are required. Found: {counts['Medium']}")
            if counts["Hard"] < 1:
                raise ValueError(f"For 5 questions, at least 1 Hard question is required. Found: {counts['Hard']}")
        elif total == 6:
            if counts["Easy"] < 1:
                raise ValueError(f"For 6 questions, at least 1 Easy question is required. Found: {counts['Easy']}")
            if counts["Medium"] < 2:
                raise ValueError(f"For 6 questions, at least 2 Medium questions are required. Found: {counts['Medium']}")
            if counts["Hard"] < 2:
                raise ValueError(f"For 6 questions, at least 2 Hard questions are required. Found: {counts['Hard']}")

        # Validate scenarios if present
        if self.scenarios:
            # Check unique scenarioIds
            seen_sids = set()
            for s in self.scenarios:
                s_id = s.scenarioId.strip().lower()
                if s_id in seen_sids:
                    raise ValueError(f"Duplicate scenarioId detected: '{s.scenarioId}'")
                seen_sids.add(s_id)

            # If multi-scenario (standard topic generation: 2-3 scenarios)
            if len(self.scenarios) >= 2:
                if len(self.scenarios) > 3:
                    raise ValueError(f"Generated scenarios count must be between 2 and 3. Received: {len(self.scenarios)}")

                # Check that both MCQ and MSQ question formats are present
                has_mcq = any(q.questionFormat == "MCQ" for q in self.questions)
                has_msq = any(q.questionFormat == "MSQ" for q in self.questions)
                if not (has_mcq and has_msq):
                    raise ValueError(
                        "Generated questions must include both MCQ (Multiple-Choice) and MSQ (Multiple-Select) formats."
                    )

        return self


# ==========================================
# API Request & Response Wrappers
# ==========================================

class TopicRequest(BaseModel):
    """Input payload for generating a scenario and questions from a topic."""
    topic: str = Field(
        ...,
        min_length=2,
        description="The topic provided by the user (e.g. 'Online Shopping', 'Database Management System')"
    )
    preferred_provider: Optional[str] = Field(
        default=None,
        description="Optional preferred LLM provider ('groq', 'openrouter', 'huggingface')"
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional model override for the provider"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional temperature override (0.0 to 1.0)"
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 2:
            raise ValueError("Topic must be at least 2 characters long to generate a meaningful scenario.")
        return trimmed


class ScenarioRequest(BaseModel):
    """Input payload supporting scenario or topic for question generation."""
    topic: Optional[str] = Field(
        default=None,
        description="The topic provided by the user"
    )
    scenario: Optional[str] = Field(
        default=None,
        description="The user-provided scenario (optional)"
    )
    scenarios: Optional[List[ScenarioItem]] = Field(
        default=None,
        description="User-provided scenarios list (optional)"
    )
    preferred_provider: Optional[str] = Field(
        default=None,
        description="Optional preferred LLM provider ('groq', 'openrouter', 'huggingface')"
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional model override for the provider"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional temperature override (0.0 to 1.0)"
    )

    @model_validator(mode="after")
    def validate_input(self) -> "ScenarioRequest":
        has_topic = bool(self.topic and self.topic.strip())
        has_scenario = bool(self.scenario and self.scenario.strip())
        has_scenarios = bool(self.scenarios and len(self.scenarios) > 0)
        if not (has_topic or has_scenario or has_scenarios):
            raise ValueError("Either 'topic', 'scenario', or 'scenarios' must be provided.")
        if self.topic:
            self.topic = self.topic.strip()
        if self.scenario:
            self.scenario = self.scenario.strip()
        return self


class GenerationMetadata(BaseModel):
    """Metadata regarding LLM execution."""
    provider_used: str
    model_used: str
    duration_seconds: float
    total_questions: int
    attempts: int
    fallback_occurred: bool = False


class ScenarioAPIResponse(BaseModel):
    """Full API response envelope for question generation."""
    success: bool = True
    message: str = "Questions generated successfully"
    data: QuestionGenerationResponse
    metadata: GenerationMetadata


class HealthResponse(BaseModel):
    """API health status response."""
    status: str = "healthy"
    version: str = "1.0.0"
    available_providers: List[str]
