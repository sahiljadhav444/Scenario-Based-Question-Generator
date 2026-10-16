"""
Tests for JSONValidator and Schema Compliance.
"""
import pytest
import json
import uuid
from app.services.json_validator import JSONValidator
from app.models.question_schema import QuestionGenerationResponse


VALID_5_QUESTIONS_PAYLOAD = {
    "topic": "Human Resources",
    "scenario": "A company wants to identify employees who earn more than $50,000 and work in the Sales department.",
    "questions": [
        {
            "questionId": "11111111-1111-4111-8111-111111111111",
            "questionType": "scenario_based",
            "difficultyTag": "Easy",
            "subject": "Human Resources / Employee Filtering",
            "questionText": "What department do the employees need to work in to meet the company's requirement?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Marketing department", "isCorrect": False},
                {"optionSequenceNo": 2, "optionText": "Sales department", "isCorrect": True},
                {"optionSequenceNo": 3, "optionText": "Engineering department", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "Finance department", "isCorrect": False},
            ],
        },
        {
            "questionId": "22222222-2222-4222-8222-222222222222",
            "questionType": "scenario_based",
            "difficultyTag": "Medium",
            "subject": "Human Resources / Employee Filtering",
            "questionText": "Which two criteria must both be satisfied for an employee to be identified by the company?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Earning more than $50,000 and working in Sales", "isCorrect": True},
                {"optionSequenceNo": 2, "optionText": "Earning exactly $50,000 or working in Sales", "isCorrect": False},
                {"optionSequenceNo": 3, "optionText": "Working in Sales regardless of salary", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "Earning more than $50,000 in any department", "isCorrect": False},
            ],
        },
        {
            "questionId": "33333333-3333-4333-8333-333333333333",
            "questionType": "scenario_based",
            "difficultyTag": "Medium",
            "subject": "Human Resources / Employee Filtering",
            "questionText": "What salary threshold must an employee exceed to qualify under the given requirement?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Greater than $50,000", "isCorrect": True},
                {"optionSequenceNo": 2, "optionText": "Equal to or less than $50,000", "isCorrect": False},
                {"optionSequenceNo": 3, "optionText": "Between $40,000 and $50,000", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "Any salary above $0", "isCorrect": False},
            ],
        },
        {
            "questionId": "44444444-4444-4444-8444-444444444444",
            "questionType": "scenario_based",
            "difficultyTag": "Hard",
            "subject": "Human Resources / Employee Filtering",
            "questionText": "If an employee works in the Sales department but earns exactly $50,000, should this employee be included in the results?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Yes, because the employee works in the Sales department", "isCorrect": False},
                {"optionSequenceNo": 2, "optionText": "No, because the requirement states earnings must be more than $50,000", "isCorrect": True},
                {"optionSequenceNo": 3, "optionText": "Yes, because $50,000 meets the minimum threshold", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "No, because the employee is not in Sales", "isCorrect": False},
            ],
        },
        {
            "questionId": "55555555-5555-4555-8555-555555555555",
            "questionType": "scenario_based",
            "difficultyTag": "Medium",
            "subject": "Human Resources / Employee Filtering",
            "questionText": "If an employee earns $65,000 in the Marketing department, why is this employee excluded?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "The employee does not meet the salary threshold", "isCorrect": False},
                {"optionSequenceNo": 2, "optionText": "The employee is not in the Sales department", "isCorrect": True},
                {"optionSequenceNo": 3, "optionText": "The employee earns too much for the requirement", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "The scenario requires employees from all departments", "isCorrect": False},
            ],
        },
    ],
}


def test_valid_json_parsing():
    """Test standard valid 5-question JSON response."""
    raw = json.dumps(VALID_5_QUESTIONS_PAYLOAD)
    validated, parsed = JSONValidator.validate_raw_response(raw)
    assert len(validated.questions) == 5
    assert validated.scenario == VALID_5_QUESTIONS_PAYLOAD["scenario"]
    assert validated.questions[0].questionId == "11111111-1111-4111-8111-111111111111"
    assert validated.questions[0].questionType == "scenario_based"
    assert validated.questions[0].difficultyTag == "Easy"
    assert validated.questions[0].optionsList[1].isCorrect is True
    assert validated.questions[0].optionsList[0].isCorrect is False


def test_valid_6_questions_parsing():
    """Test valid 6-question JSON response with valid distribution (1 Easy, 2 Medium, 2 Hard, 1 any)."""
    payload_6 = dict(VALID_5_QUESTIONS_PAYLOAD)
    payload_6["questions"] = list(VALID_5_QUESTIONS_PAYLOAD["questions"]) + [
        {
            "questionId": "66666666-6666-4666-8666-666666666666",
            "questionType": "scenario_based",
            "difficultyTag": "Hard",
            "subject": "Human Resources / Employee Filtering",
            "questionText": "What is the logical outcome when evaluating a candidate earning $52,000 in Sales versus $48,000 in Sales?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Only the employee earning $52,000 is included", "isCorrect": True},
                {"optionSequenceNo": 2, "optionText": "Both employees are included because both are in Sales", "isCorrect": False},
                {"optionSequenceNo": 3, "optionText": "Neither employee is included", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "Only the employee earning $48,000 is included", "isCorrect": False},
            ],
        }
    ]
    raw = json.dumps(payload_6)
    validated, _ = JSONValidator.validate_raw_response(raw)
    assert len(validated.questions) == 6


def test_markdown_codeblock_extraction():
    """Test extracting JSON wrapped in markdown backticks ```json ... ```"""
    raw = f"Here is the generated output:\n```json\n{json.dumps(VALID_5_QUESTIONS_PAYLOAD)}\n```\nHope this helps!"
    validated, _ = JSONValidator.validate_raw_response(raw)
    assert len(validated.questions) == 5


def test_conversational_text_outside_json():
    """Test extracting JSON with conversational preamble and epilogue."""
    raw = f"Sure! Here are your questions:\n{json.dumps(VALID_5_QUESTIONS_PAYLOAD)}\nLet me know if you need anything else."
    validated, _ = JSONValidator.validate_raw_response(raw)
    assert len(validated.questions) == 5


def test_trailing_commas_sanitization():
    """Test that trailing commas in JSON are safely removed before parsing."""
    malformed_json_str = """
    {
      "scenario": "A company wants to identify employees who earn more than $50,000 and work in the Sales department.",
      "questions": [
        {
          "questionId": "11111111-1111-4111-8111-111111111111",
          "questionType": "scenario_based",
          "difficultyTag": "Easy",
          "subject": "HR",
          "questionText": "Question 1 text?",
          "optionsList": [
            {"optionSequenceNo": 1, "optionText": "Opt 1", "isCorrect": true},
            {"optionSequenceNo": 2, "optionText": "Opt 2", "isCorrect": false},
            {"optionSequenceNo": 3, "optionText": "Opt 3", "isCorrect": false},
            {"optionSequenceNo": 4, "optionText": "Opt 4", "isCorrect": false},
          ],
        },
        {
          "questionId": "22222222-2222-4222-8222-222222222222",
          "questionType": "scenario_based",
          "difficultyTag": "Medium",
          "subject": "HR",
          "questionText": "Question 2 text?",
          "optionsList": [
            {"optionSequenceNo": 1, "optionText": "Opt A", "isCorrect": false},
            {"optionSequenceNo": 2, "optionText": "Opt B", "isCorrect": true},
            {"optionSequenceNo": 3, "optionText": "Opt C", "isCorrect": false},
            {"optionSequenceNo": 4, "optionText": "Opt D", "isCorrect": false}
          ]
        },
        {
          "questionId": "33333333-3333-4333-8333-333333333333",
          "questionType": "scenario_based",
          "difficultyTag": "Medium",
          "subject": "HR",
          "questionText": "Question 3 text?",
          "optionsList": [
            {"optionSequenceNo": 1, "optionText": "Opt A", "isCorrect": false},
            {"optionSequenceNo": 2, "optionText": "Opt B", "isCorrect": true},
            {"optionSequenceNo": 3, "optionText": "Opt C", "isCorrect": false},
            {"optionSequenceNo": 4, "optionText": "Opt D", "isCorrect": false}
          ]
        },
        {
          "questionId": "44444444-4444-4444-8444-444444444444",
          "questionType": "scenario_based",
          "difficultyTag": "Hard",
          "subject": "HR",
          "questionText": "Question 4 text?",
          "optionsList": [
            {"optionSequenceNo": 1, "optionText": "Opt A", "isCorrect": false},
            {"optionSequenceNo": 2, "optionText": "Opt B", "isCorrect": true},
            {"optionSequenceNo": 3, "optionText": "Opt C", "isCorrect": false},
            {"optionSequenceNo": 4, "optionText": "Opt D", "isCorrect": false}
          ]
        },
        {
          "questionId": "55555555-5555-4555-8555-555555555555",
          "questionType": "scenario_based",
          "difficultyTag": "Medium",
          "subject": "HR",
          "questionText": "Question 5 text?",
          "optionsList": [
            {"optionSequenceNo": 1, "optionText": "Opt A", "isCorrect": false},
            {"optionSequenceNo": 2, "optionText": "Opt B", "isCorrect": true},
            {"optionSequenceNo": 3, "optionText": "Opt C", "isCorrect": false},
            {"optionSequenceNo": 4, "optionText": "Opt D", "isCorrect": false}
          ]
        }
      ]
    }
    """
    validated, _ = JSONValidator.validate_raw_response(malformed_json_str)
    assert len(validated.questions) == 5


def test_fails_on_less_than_5_questions():
    """Test validation fails if only 4 questions are generated."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": VALID_5_QUESTIONS_PAYLOAD["questions"][:4]
    }
    with pytest.raises(ValueError, match="between 5 and 6"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_more_than_6_questions():
    """Test validation fails if 7 questions are generated."""
    extra_q = dict(VALID_5_QUESTIONS_PAYLOAD["questions"][0], questionId=str(uuid.uuid4()))
    extra_q2 = dict(VALID_5_QUESTIONS_PAYLOAD["questions"][1], questionId=str(uuid.uuid4()))
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": VALID_5_QUESTIONS_PAYLOAD["questions"] + [extra_q, extra_q2]
    }
    with pytest.raises(ValueError, match="between 5 and 6"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_non_four_options():
    """Test validation fails if a question has 3 options."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            {
                "questionId": "11111111-1111-4111-8111-111111111111",
                "questionType": "scenario_based",
                "difficultyTag": "Easy",
                "subject": "HR",
                "questionText": "Question with 3 options?",
                "optionsList": [
                    {"optionSequenceNo": 1, "optionText": "Opt 1", "isCorrect": True},
                    {"optionSequenceNo": 2, "optionText": "Opt 2", "isCorrect": False},
                    {"optionSequenceNo": 3, "optionText": "Opt 3", "isCorrect": False},
                ]
            }
        ] + VALID_5_QUESTIONS_PAYLOAD["questions"][1:]
    }
    with pytest.raises(ValueError, match="exactly 4 options"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_multiple_correct_options():
    """Test validation fails if a question has 2 correct options."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            {
                "questionId": "11111111-1111-4111-8111-111111111111",
                "questionType": "scenario_based",
                "difficultyTag": "Easy",
                "subject": "HR",
                "questionText": "Question with two true options?",
                "optionsList": [
                    {"optionSequenceNo": 1, "optionText": "Opt 1", "isCorrect": True},
                    {"optionSequenceNo": 2, "optionText": "Opt 2", "isCorrect": True},
                    {"optionSequenceNo": 3, "optionText": "Opt 3", "isCorrect": False},
                    {"optionSequenceNo": 4, "optionText": "Opt 4", "isCorrect": False},
                ]
            }
        ] + VALID_5_QUESTIONS_PAYLOAD["questions"][1:]
    }
    with pytest.raises(ValueError, match="Exactly ONE option must have isCorrect: true"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_zero_correct_options():
    """Test validation fails if a question has 0 correct options."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            {
                "questionId": "11111111-1111-4111-8111-111111111111",
                "questionType": "scenario_based",
                "difficultyTag": "Easy",
                "subject": "HR",
                "questionText": "Question with zero true options?",
                "optionsList": [
                    {"optionSequenceNo": 1, "optionText": "Opt 1", "isCorrect": False},
                    {"optionSequenceNo": 2, "optionText": "Opt 2", "isCorrect": False},
                    {"optionSequenceNo": 3, "optionText": "Opt 3", "isCorrect": False},
                    {"optionSequenceNo": 4, "optionText": "Opt 4", "isCorrect": False},
                ]
            }
        ] + VALID_5_QUESTIONS_PAYLOAD["questions"][1:]
    }
    with pytest.raises(ValueError, match="Exactly ONE option must have isCorrect: true"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_duplicate_options():
    """Test validation fails if options within a question are duplicates."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            {
                "questionId": "11111111-1111-4111-8111-111111111111",
                "questionType": "scenario_based",
                "difficultyTag": "Easy",
                "subject": "HR",
                "questionText": "Question with duplicate options?",
                "optionsList": [
                    {"optionSequenceNo": 1, "optionText": "Same option", "isCorrect": True},
                    {"optionSequenceNo": 2, "optionText": "same option", "isCorrect": False},
                    {"optionSequenceNo": 3, "optionText": "Unique option 3", "isCorrect": False},
                    {"optionSequenceNo": 4, "optionText": "Unique option 4", "isCorrect": False},
                ]
            }
        ] + VALID_5_QUESTIONS_PAYLOAD["questions"][1:]
    }
    with pytest.raises(ValueError, match="Duplicate option found"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_duplicate_question_ids():
    """Test validation fails if question IDs are duplicate."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][0], questionId="11111111-1111-4111-8111-111111111111"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][1], questionId="11111111-1111-4111-8111-111111111111"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][2], questionId="33333333-3333-4333-8333-333333333333"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][3], questionId="44444444-4444-4444-8444-444444444444"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][4], questionId="55555555-5555-4555-8555-555555555555"),
        ]
    }
    with pytest.raises(ValueError, match="Duplicate questionId detected"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_prohibited_all_of_the_above_option():
    """Test rejection of 'All of the above' options."""
    data = {
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            {
                "questionId": "11111111-1111-4111-8111-111111111111",
                "questionType": "scenario_based",
                "difficultyTag": "Easy",
                "subject": "HR",
                "questionText": "Question with prohibited option?",
                "optionsList": [
                    {"optionSequenceNo": 1, "optionText": "Specific option", "isCorrect": False},
                    {"optionSequenceNo": 2, "optionText": "Another option", "isCorrect": False},
                    {"optionSequenceNo": 3, "optionText": "Third option", "isCorrect": False},
                    {"optionSequenceNo": 4, "optionText": "All of the above", "isCorrect": True},
                ]
            }
        ] + VALID_5_QUESTIONS_PAYLOAD["questions"][1:]
    }
    with pytest.raises(ValueError, match="is prohibited"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_fails_on_invalid_difficulty_distribution():
    """Test rejection when 5 questions has 0 Hard questions."""
    data = {
        "topic": "Human Resources",
        "scenario": VALID_5_QUESTIONS_PAYLOAD["scenario"],
        "questions": [
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][0], difficultyTag="Easy"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][1], difficultyTag="Easy"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][2], difficultyTag="Medium"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][3], difficultyTag="Medium"),
            dict(VALID_5_QUESTIONS_PAYLOAD["questions"][4], difficultyTag="Medium"),
        ]
    }
    with pytest.raises(ValueError, match="at least 1 Hard question is required"):
        JSONValidator.validate_raw_response(json.dumps(data))


def test_validate_generated_scenario():
    """Test scenario cleaning, label stripping, and length validation."""
    raw = '  **Scenario:** "A customer attempts to checkout an item online, but the payment gateway fails."  '
    cleaned = JSONValidator.validate_generated_scenario(raw)
    assert cleaned == "A customer attempts to checkout an item online, but the payment gateway fails."

    # Fails on empty or too short
    with pytest.raises(ValueError, match="cannot be empty"):
        JSONValidator.validate_generated_scenario("")

    with pytest.raises(ValueError, match="too short"):
        JSONValidator.validate_generated_scenario("Too short")


VALID_MULTI_SCENARIO_PAYLOAD = {
    "topic": "Online Hospital Appointment Booking System",
    "scenarios": [
        {
            "scenarioId": "11111111-1111-4111-8111-111111111111",
            "scenarioText": "A patient attempts to book an appointment with a cardiologist using the mobile hospital app. The app allows booking up to 14 days in advance, but requires a pre-existing doctor referral uploaded as a PDF."
        },
        {
            "scenarioId": "22222222-2222-4222-8222-222222222222",
            "scenarioText": "A specialist clinic manages emergency walk-in consultations where nurses assign high priority to patients with chest pains and moderate priority to patients with fever."
        }
    ],
    "questions": [
        {
            "questionId": "aaaaaaa1-1111-4111-8111-111111111111",
            "questionType": "scenario_based",
            "questionFormat": "MCQ",
            "difficultyTag": "Easy",
            "subject": "Hospital Scheduling",
            "questionText": "How many days in advance does the hospital mobile app permit cardiology appointments to be booked?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "7 days in advance", "isCorrect": False},
                {"optionSequenceNo": 2, "optionText": "14 days in advance", "isCorrect": True},
                {"optionSequenceNo": 3, "optionText": "30 days in advance", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "Same-day only", "isCorrect": False}
            ]
        },
        {
            "questionId": "aaaaaaa2-2222-4222-8222-222222222222",
            "questionType": "scenario_based",
            "questionFormat": "MSQ",
            "difficultyTag": "Medium",
            "subject": "Hospital Scheduling",
            "questionText": "Which requirements must be met to book a cardiology appointment through the app? (Select all that apply)",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Upload a doctor referral in PDF format", "isCorrect": True},
                {"optionSequenceNo": 2, "optionText": "Schedule within 14 days in advance", "isCorrect": True},
                {"optionSequenceNo": 3, "optionText": "Provide in-person paper referral at check-in", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "Book at least 30 days ahead", "isCorrect": False}
            ]
        },
        {
            "questionId": "aaaaaaa3-3333-4333-8333-333333333333",
            "questionType": "scenario_based",
            "questionFormat": "MCQ",
            "difficultyTag": "Medium",
            "subject": "Hospital Scheduling",
            "questionText": "What priority is assigned to a walk-in patient complaining of chest pain?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Low priority", "isCorrect": False},
                {"optionSequenceNo": 2, "optionText": "Moderate priority", "isCorrect": False},
                {"optionSequenceNo": 3, "optionText": "High priority", "isCorrect": True},
                {"optionSequenceNo": 4, "optionText": "Deferred priority", "isCorrect": False}
            ]
        },
        {
            "questionId": "aaaaaaa4-4444-4444-8444-444444444444",
            "questionType": "scenario_based",
            "questionFormat": "MSQ",
            "difficultyTag": "Hard",
            "subject": "Hospital Scheduling",
            "questionText": "Based on the emergency walk-in protocol, which statements accurately reflect the clinic priority guidelines? (Select all that apply)",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "Patients with fever receive moderate priority", "isCorrect": True},
                {"optionSequenceNo": 2, "optionText": "Patients with chest pain receive high priority", "isCorrect": True},
                {"optionSequenceNo": 3, "optionText": "Patients with fever are treated before chest pain patients", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "All walk-ins are treated on a first-come, first-served basis regardless of condition", "isCorrect": False}
            ]
        },
        {
            "questionId": "aaaaaaa5-5555-4555-8555-555555555555",
            "questionType": "scenario_based",
            "questionFormat": "MCQ",
            "difficultyTag": "Medium",
            "subject": "Hospital Scheduling",
            "questionText": "If a patient attempts to book a cardiology appointment 20 days in advance with a valid PDF referral, what is the expected outcome?",
            "optionsList": [
                {"optionSequenceNo": 1, "optionText": "The appointment is rejected because it exceeds the 14-day limit", "isCorrect": True},
                {"optionSequenceNo": 2, "optionText": "The appointment is accepted immediately", "isCorrect": False},
                {"optionSequenceNo": 3, "optionText": "The appointment is converted to an emergency walk-in", "isCorrect": False},
                {"optionSequenceNo": 4, "optionText": "The patient is redirected to moderate priority", "isCorrect": False}
            ]
        }
    ]
}


def test_valid_multi_scenario_payload():
    """Test valid response with 2 scenarios and 5 questions (both MCQ and MSQ)."""
    raw = json.dumps(VALID_MULTI_SCENARIO_PAYLOAD)
    validated, parsed = JSONValidator.validate_raw_response(raw)
    assert len(validated.scenarios) == 2
    assert len(validated.questions) == 5
    assert any(q.questionFormat == "MCQ" for q in validated.questions)
    assert any(q.questionFormat == "MSQ" for q in validated.questions)
    for q in validated.questions:
        assert not hasattr(q, "calculationDraft")
        assert not hasattr(q, "scenarioId")


def test_validate_generated_scenarios():
    """Test parsing and validating 2 distinct scenarios generated from topic."""
    scenarios_json = json.dumps({
        "topic": "Online Hospital Appointment Booking System",
        "scenarios": [
            {
                "scenarioId": "11111111-1111-4111-8111-111111111111",
                "scenarioText": "A patient attempts to book an appointment with a cardiologist using the mobile hospital app."
            },
            {
                "scenarioId": "22222222-2222-4222-8222-222222222222",
                "scenarioText": "A specialist clinic manages emergency walk-in consultations where nurses assign priority."
            }
        ]
    })
    scenarios = JSONValidator.validate_generated_scenarios(scenarios_json, topic="Hospital")
    assert len(scenarios) == 2
    assert scenarios[0].scenarioId == "11111111-1111-4111-8111-111111111111"
    assert "cardiologist" in scenarios[0].scenarioText


def test_validate_generated_scenarios_fails_on_single_scenario():
    """Test that generating fewer than 2 scenarios fails validation."""
    scenarios_json = json.dumps({
        "scenarios": [
            {
                "scenarioId": "11111111-1111-4111-8111-111111111111",
                "scenarioText": "Only a single scenario text here that is long enough."
            }
        ]
    })
    with pytest.raises(ValueError, match="Expected exactly 2 or 3 distinct scenarios"):
        JSONValidator.validate_generated_scenarios(scenarios_json)


def test_validate_generated_scenarios_fails_on_more_than_three():
    """Test that generating more than 3 scenarios fails validation."""
    scenarios_json = json.dumps({
        "scenarios": [
            {"scenarioId": str(uuid.uuid4()), "scenarioText": "First scenario text that is long enough."},
            {"scenarioId": str(uuid.uuid4()), "scenarioText": "Second scenario text that is long enough."},
            {"scenarioId": str(uuid.uuid4()), "scenarioText": "Third scenario text that is long enough."},
            {"scenarioId": str(uuid.uuid4()), "scenarioText": "Fourth scenario text that is long enough."},
        ]
    })
    with pytest.raises(ValueError, match="Expected exactly 2 or 3 distinct scenarios"):
        JSONValidator.validate_generated_scenarios(scenarios_json)


def test_fails_when_all_questions_are_mcq_in_multi_scenario():
    """Test validation fails when multi-scenario has no MSQ questions."""
    payload = json.loads(json.dumps(VALID_MULTI_SCENARIO_PAYLOAD))
    # Convert all MSQ questions to MCQ with 1 correct option
    for q in payload["questions"]:
        q["questionFormat"] = "MCQ"
        for opt in q["optionsList"]:
            opt["isCorrect"] = (opt["optionSequenceNo"] == 1)

    with pytest.raises(ValueError, match="must include both MCQ .* and MSQ"):
        JSONValidator.validate_raw_response(json.dumps(payload))


def test_fails_when_all_questions_are_msq_in_multi_scenario():
    """Test validation fails when multi-scenario has no MCQ questions."""
    payload = json.loads(json.dumps(VALID_MULTI_SCENARIO_PAYLOAD))
    # Convert all MCQ questions to MSQ with 2 correct options
    for q in payload["questions"]:
        q["questionFormat"] = "MSQ"
        for opt in q["optionsList"]:
            opt["isCorrect"] = (opt["optionSequenceNo"] in (1, 2))

    with pytest.raises(ValueError, match="must include both MCQ .* and MSQ"):
        JSONValidator.validate_raw_response(json.dumps(payload))


def test_fails_when_msq_has_fewer_than_two_correct_options():
    """Test validation fails when an MSQ question has only 1 correct option."""
    payload = json.loads(json.dumps(VALID_MULTI_SCENARIO_PAYLOAD))
    # Find MSQ and make only 1 correct option
    for q in payload["questions"]:
        if q["questionFormat"] == "MSQ":
            for opt in q["optionsList"]:
                opt["isCorrect"] = (opt["optionSequenceNo"] == 1)
            break

    with pytest.raises(ValueError, match="At least TWO options must have isCorrect: true"):
        JSONValidator.validate_raw_response(json.dumps(payload))


def test_extra_fields_stripped_from_questions():
    """Test that scenarioId and calculationDraft on questions are safely stripped/ignored."""
    payload = json.loads(json.dumps(VALID_MULTI_SCENARIO_PAYLOAD))
    for q in payload["questions"]:
        q["scenarioId"] = "11111111-1111-4111-8111-111111111111"
        q["calculationDraft"] = "Should be stripped"

    validated = JSONValidator.validate_schema(payload)
    for q in validated.questions:
        assert not hasattr(q, "calculationDraft")
        assert not hasattr(q, "scenarioId")



