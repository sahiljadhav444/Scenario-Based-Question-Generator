"""
Robust JSON Sanitizer and Schema Validator for Question Generation.
"""
import json
import re
import uuid
from typing import Any, Dict, Optional, Tuple
from pydantic import ValidationError
from app.models.question_schema import QuestionGenerationResponse
from app.utils.logger import get_logger

logger = get_logger("JSONValidator")


class JSONValidator:
    """
    Sanitizes raw LLM output, strips markdown delimiters,
    normalizes fields where appropriate, and validates strictly
    against the QuestionGenerationResponse Pydantic schema.
    """

    @staticmethod
    def extract_json_content(raw_text: str) -> str:
        """
        Extracts clean JSON string from raw LLM output.
        Handles markdown codeblocks, conversational preambles, and postambles.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("LLM returned an empty response.")

        text = raw_text.strip()

        # Step 1: Strip markdown codeblocks (```json ... ``` or ``` ... ```)
        codeblock_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if codeblock_match:
            text = codeblock_match.group(1).strip()

        # Step 2: Find outermost JSON object braces { ... }
        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx : end_idx + 1]
        else:
            raise ValueError("No JSON object '{ ... }' detected in LLM output.")

        # Step 3: Remove trailing commas before } or ] which invalidate JSON
        text = re.sub(r",\s*([\]}])", r"\1", text)

        return text

    @classmethod
    def parse_to_dict(cls, raw_text: str) -> Dict[str, Any]:
        """Parses raw text to a Python dictionary after sanitization."""
        cleaned_json = cls.extract_json_content(raw_text)
        try:
            return json.loads(cleaned_json)
        except json.JSONDecodeError as err:
            logger.error(f"JSON decode failed: {err}. Cleaned text was:\n{cleaned_json}")
            raise ValueError(f"Invalid JSON syntax: {err.msg} at line {err.lineno} col {err.colno}") from err

    @staticmethod
    def validate_generated_scenario(scenario_text: str) -> str:
        """
        Cleans and validates the raw scenario generated from a topic.
        Strips markdown wrappers, unwanted labels, and ensures non-empty meaningful text.
        """
        if not scenario_text or not scenario_text.strip():
            raise ValueError("Generated scenario cannot be empty.")

        cleaned = scenario_text.strip()

        # Strip markdown code blocks if wrapped
        codeblock_match = re.search(r"```(?:text|markdown)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if codeblock_match:
            cleaned = codeblock_match.group(1).strip()

        # Remove leading "Scenario:" or "**Scenario:**" or "Generated Scenario:" labels
        cleaned = re.sub(
            r"^\*{0,2}(?:Scenario|Generated Scenario)\*{0,2}\s*:\s*\*{0,2}",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # Strip surrounding double or single quotes and asterisks
        cleaned = cleaned.strip('"').strip("'").strip("*").strip('"').strip("'").strip()

        if len(cleaned) < 15:
            raise ValueError(
                f"Generated scenario is too short ({len(cleaned)} chars) to generate meaningful questions: '{cleaned}'"
            )

        return cleaned

    @classmethod
    def normalize_payload(
        cls,
        data: Dict[str, Any],
        fallback_scenario: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes minor structural discrepancies from LLM output:
        - Injects topic if top-level topic was omitted or requested.
        - Injects fallback scenario if top-level scenario was omitted or provided.
        - Ensures questionId is a valid UUID string.
        - Ensures optionSequenceNo is assigned (1, 2, 3, 4).
        - Ensures questionType defaults to 'scenario_based'.
        """
        if not isinstance(data, dict):
            return data

        # Ensure topic exists and is aligned
        if topic and topic.strip():
            data["topic"] = topic.strip()
        elif "topic" not in data or not data["topic"]:
            data["topic"] = "Scenario Assessment"

        # Ensure scenario exists and is aligned
        if fallback_scenario and fallback_scenario.strip():
            data["scenario"] = fallback_scenario.strip()
        elif "scenario" not in data or not data["scenario"]:
            data["scenario"] = ""

        questions = data.get("questions")
        if isinstance(questions, list):
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    continue

                # Ensure questionType is scenario_based
                if "questionType" not in q or not q["questionType"]:
                    q["questionType"] = "scenario_based"

                # Ensure subject is set
                if "subject" not in q or not q["subject"]:
                    q["subject"] = data.get("topic") or "Scenario Assessment"

                # Ensure valid UUID questionId
                raw_qid = str(q.get("questionId", "")).strip()
                try:
                    uuid.UUID(raw_qid)
                except (ValueError, AttributeError):
                    # Generate a valid UUID if missing or non-UUID
                    q["questionId"] = str(uuid.uuid4())

                # Normalize optionsList
                options = q.get("optionsList") or q.get("options")
                if isinstance(options, list):
                    q["optionsList"] = options
                    for opt_idx, opt in enumerate(options, start=1):
                        if isinstance(opt, dict):
                            # Ensure sequence number
                            if "optionSequenceNo" not in opt or not isinstance(opt["optionSequenceNo"], int):
                                opt["optionSequenceNo"] = opt_idx
                            # Normalize camelCase vs snake_case if LLM returned option_text / is_correct
                            if "optionText" not in opt and "option_text" in opt:
                                opt["optionText"] = opt["option_text"]
                            if "isCorrect" not in opt and "is_correct" in opt:
                                opt["isCorrect"] = opt["is_correct"]

        return data

    @classmethod
    def validate_schema(
        cls,
        data: Dict[str, Any],
        fallback_scenario: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> QuestionGenerationResponse:
        """Validates a dictionary against the QuestionGenerationResponse schema."""
        normalized = cls.normalize_payload(data, fallback_scenario=fallback_scenario, topic=topic)
        try:
            return QuestionGenerationResponse.model_validate(normalized)
        except ValidationError as val_err:
            error_details = []
            for err in val_err.errors():
                loc = " -> ".join(str(p) for p in err.get("loc", []))
                msg = err.get("msg", "")
                error_details.append(f"[{loc}]: {msg}")
            full_msg = "; ".join(error_details)
            logger.warning(f"Schema validation failed: {full_msg}")
            raise ValueError(f"Validation failed: {full_msg}") from val_err

    @classmethod
    def validate_raw_response(
        cls,
        raw_text: str,
        fallback_scenario: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Tuple[QuestionGenerationResponse, Dict[str, Any]]:
        """
        End-to-end pipeline: sanitize, parse, normalize, validate, and return model and dict.
        """
        parsed_dict = cls.parse_to_dict(raw_text)
        validated_model = cls.validate_schema(parsed_dict, fallback_scenario=fallback_scenario, topic=topic)
        return validated_model, parsed_dict


# Global validator instance
json_validator = JSONValidator()
