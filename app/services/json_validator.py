"""
Robust JSON Sanitizer and Schema Validator for Question Generation.
"""
import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import ValidationError
from app.models.question_schema import QuestionGenerationResponse, ScenarioItem
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

        # Step 2: Find outermost JSON object or array braces { ... } or [ ... ]
        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx : end_idx + 1]
        else:
            # Check for array
            arr_start = text.find("[")
            arr_end = text.rfind("]")
            if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
                text = text[arr_start : arr_end + 1]
            else:
                raise ValueError("No JSON object '{ ... }' detected in LLM output.")

        # Step 3: Remove trailing commas before } or ] which invalidate JSON
        text = re.sub(r",\s*([\]}])", r"\1", text)

        return text

    @classmethod
    def parse_to_dict(cls, raw_text: str) -> Union[Dict[str, Any], list]:
        """Parses raw text to a Python dictionary or list after sanitization."""
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
    def validate_generated_scenarios(
        cls,
        raw_text: str,
        topic: Optional[str] = None,
    ) -> List[ScenarioItem]:
        """
        Parses and validates 2 to 3 distinct scenarios generated from a topic.
        Ensures each scenario is valid, non-empty, and has a unique UUID.
        """
        parsed = cls.parse_to_dict(raw_text)
        scenarios_raw = []

        if isinstance(parsed, dict):
            scenarios_raw = parsed.get("scenarios") or parsed.get("scenario_list") or []
        elif isinstance(parsed, list):
            scenarios_raw = parsed

        if not scenarios_raw or not isinstance(scenarios_raw, list):
            raise ValueError("LLM output did not contain a valid 'scenarios' list.")

        scenario_items: List[ScenarioItem] = []
        seen_texts = set()

        for idx, item in enumerate(scenarios_raw, 1):
            if isinstance(item, dict):
                raw_id = str(item.get("scenarioId") or item.get("scenario_id") or uuid.uuid4()).strip()
                try:
                    sc_id = str(uuid.UUID(raw_id))
                except ValueError:
                    sc_id = str(uuid.uuid4())

                text = item.get("scenarioText") or item.get("scenario_text") or item.get("text") or item.get("scenario") or ""
                cleaned_text = cls.validate_generated_scenario(str(text))
            elif isinstance(item, str):
                sc_id = str(uuid.uuid4())
                cleaned_text = cls.validate_generated_scenario(item)
            else:
                continue

            # Check duplicate scenarios
            normalized_text = cleaned_text.lower()
            if normalized_text in seen_texts:
                raise ValueError(f"Duplicate scenario generated: '{cleaned_text[:50]}...'")
            seen_texts.add(normalized_text)

            scenario_items.append(ScenarioItem(scenarioId=sc_id, scenarioText=cleaned_text))

        if not (2 <= len(scenario_items) <= 3):
            raise ValueError(
                f"Expected exactly 2 or 3 distinct scenarios, but received {len(scenario_items)}."
            )

        return scenario_items

    @classmethod
    def normalize_payload(
        cls,
        data: Dict[str, Any],
        fallback_scenarios: Optional[List[Any]] = None,
        fallback_scenario: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes minor structural discrepancies from LLM output:
        - Injects topic if top-level topic was omitted or requested.
        - Injects fallback scenarios or single scenario if omitted.
        - Ensures scenarioId and questionId are valid UUID strings.
        - Normalizes questionFormat to 'MCQ' or 'MSQ'.
        - Ensures calculationDraft is populated.
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

        # Normalize scenarios
        if "scenarios" in data and isinstance(data["scenarios"], list) and len(data["scenarios"]) > 0:
            normalized_scs = []
            for idx, sc in enumerate(data["scenarios"]):
                if isinstance(sc, dict):
                    sid = str(sc.get("scenarioId") or sc.get("scenario_id") or uuid.uuid4()).strip()
                    try:
                        valid_sid = str(uuid.UUID(sid))
                    except ValueError:
                        valid_sid = str(uuid.uuid4())
                    stext = str(sc.get("scenarioText") or sc.get("scenario_text") or sc.get("scenario") or "").strip()
                    normalized_scs.append({"scenarioId": valid_sid, "scenarioText": stext})
                elif isinstance(sc, str):
                    normalized_scs.append({"scenarioId": str(uuid.uuid4()), "scenarioText": sc.strip()})
            data["scenarios"] = normalized_scs
            if not data.get("scenario") and len(normalized_scs) == 1:
                data["scenario"] = normalized_scs[0]["scenarioText"]
        elif fallback_scenarios and len(fallback_scenarios) > 0:
            normalized_scs = []
            for sc in fallback_scenarios:
                if hasattr(sc, "scenarioId") and hasattr(sc, "scenarioText"):
                    normalized_scs.append({"scenarioId": sc.scenarioId, "scenarioText": sc.scenarioText})
                elif isinstance(sc, dict):
                    sid = str(sc.get("scenarioId") or sc.get("scenario_id") or uuid.uuid4()).strip()
                    try:
                        valid_sid = str(uuid.UUID(sid))
                    except ValueError:
                        valid_sid = str(uuid.uuid4())
                    stext = str(sc.get("scenarioText") or sc.get("scenario_text") or "").strip()
                    normalized_scs.append({"scenarioId": valid_sid, "scenarioText": stext})
            data["scenarios"] = normalized_scs
            if not data.get("scenario") and len(normalized_scs) == 1:
                data["scenario"] = normalized_scs[0]["scenarioText"]
        elif fallback_scenario and fallback_scenario.strip():
            sc_id = str(uuid.uuid4())
            data["scenario"] = fallback_scenario.strip()
            data["scenarios"] = [{"scenarioId": sc_id, "scenarioText": fallback_scenario.strip()}]
        elif data.get("scenario") and str(data["scenario"]).strip():
            sc_id = str(uuid.uuid4())
            data["scenario"] = str(data["scenario"]).strip()
            data["scenarios"] = [{"scenarioId": sc_id, "scenarioText": data["scenario"]}]

        valid_sids = [
            s["scenarioId"] for s in data.get("scenarios", []) if isinstance(s, dict) and "scenarioId" in s
        ]

        # Normalize questions
        questions = data.get("questions")
        if isinstance(questions, list):
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    continue

                # Strip question-level scenarioId and calculationDraft if present from LLM
                q.pop("scenarioId", None)
                q.pop("scenario_id", None)
                q.pop("calculationDraft", None)
                q.pop("calculation_draft", None)

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
                    q["questionId"] = str(uuid.uuid4())

                # Normalize questionFormat ('MCQ' or 'MSQ')
                if "questionFormat" not in q and "question_format" in q:
                    q["questionFormat"] = q["question_format"]
                if "questionFormat" not in q or not q["questionFormat"]:
                    q["questionFormat"] = "MCQ"
                else:
                    fmt = str(q["questionFormat"]).strip().upper()
                    q["questionFormat"] = "MSQ" if fmt == "MSQ" else "MCQ"

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
        fallback_scenarios: Optional[List[Any]] = None,
        fallback_scenario: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> QuestionGenerationResponse:
        """Validates a dictionary against the QuestionGenerationResponse schema."""
        normalized = cls.normalize_payload(
            data,
            fallback_scenarios=fallback_scenarios,
            fallback_scenario=fallback_scenario,
            topic=topic,
        )
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
        fallback_scenarios: Optional[List[Any]] = None,
        fallback_scenario: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Tuple[QuestionGenerationResponse, Dict[str, Any]]:
        """
        End-to-end pipeline: sanitize, parse, normalize, validate, and return model and dict.
        """
        parsed_dict = cls.parse_to_dict(raw_text)
        if not isinstance(parsed_dict, dict):
            raise ValueError("Expected top-level JSON object with 'topic', 'scenarios', and 'questions'.")
        validated_model = cls.validate_schema(
            parsed_dict,
            fallback_scenarios=fallback_scenarios,
            fallback_scenario=fallback_scenario,
            topic=topic,
        )
        return validated_model, parsed_dict


# Global validator instance
json_validator = JSONValidator()

