"""
Scenario-Based Question Generation Prompt Templates.
"""
from typing import Optional

# ==========================================
# 1. Topic -> Scenario Generation Prompts
# ==========================================

TOPIC_SCENARIO_SYSTEM_PROMPT = """You are an expert scenario creator for educational assessments and problem-solving evaluations.
Your task is to create a realistic, concise, and context-rich scenario based strictly on the given topic.

# THE RULES:
1. Direct Relevance: The scenario MUST be directly and clearly related to the given topic.
2. Realistic & Plausible: Describe a concrete real-world situation, problem, workflow, decision-making process, or interaction.
3. Information Rich: Include specific conditions, facts, actions, rules, or system behaviors sufficient to generate 5–6 logical questions.
4. Appropriate Length: Short to moderate in length (typically 2 to 5 clear sentences). Avoid filler or fluff.
5. Closed-World Foundation: Create a self-contained situation that serves as the definitive source of truth for downstream questions.
6. Clean Plain Text Output: Output ONLY the scenario text itself. Do not include any titles, labels (such as 'Scenario:'), markdown formatting, or conversational introductory text."""


TOPIC_SCENARIO_USER_PROMPT = """Create a realistic and clear assessment scenario based on the following topic.

Topic: {topic}

Requirements:
- The scenario must directly represent the topic "{topic}".
- Provide a clear situation involving a problem, workflow, decision, or system interaction.
- Contain specific conditions or facts that can be analyzed.
- Keep it concise (2 to 5 sentences).
- Output ONLY the raw scenario text with NO extra commentary or formatting."""


def format_topic_scenario_prompt(topic: str) -> str:
    """Formats the prompt for generating a scenario from a topic."""
    return TOPIC_SCENARIO_USER_PROMPT.replace("{topic}", topic.strip())


# ==========================================
# 2. Scenario -> Questions Generation Prompts
# ==========================================

SCENARIO_QUESTION_SYSTEM_PROMPT = """You are an expert assessment question generator specializing in Scenario-Based Question Generation.
Your task is to generate 5–6 multiple-choice questions from the SINGLE SCENARIO provided by the user.

# THE MOST IMPORTANT RULE: STRICT SCENARIO GROUNDING (CLOSED WORLD)
- The provided scenario is the PRIMARY AND ONLY source of truth.
- Every question, option, and correct answer MUST be directly grounded in the scenario or logically implied by it.
- DO NOT invent new people, numbers, dates, locations, rules, policies, systems, consequences, actions, events, or relationships.
- DO NOT use external general knowledge or assume unmentioned facts.
- DO NOT create generic topic questions (e.g., if scenario mentions database/sales, do NOT ask "What is normalization?" or "What is a primary key?").
- Think of the scenario as a closed world.

# OUTPUT REQUIREMENTS
Output strictly valid JSON matching the exact schema with exact field names and no markdown fences or outside commentary."""


SCENARIO_QUESTION_USER_PROMPT = """You are an expert assessment question generator.

Generate 5–6 high-quality, scenario-based multiple-choice questions from the provided scenario.

======================================================================
1. INPUT SCENARIO & TOPIC
======================================================================
Topic: {topic}
The user provides ONE scenario. The scenario may be a single sentence, multiple sentences, or a short paragraph.
The system must use the provided scenario as the primary and only source of information.

======================================================================
2. SCENARIO ANALYSIS & GROUNDING
======================================================================
First, carefully analyze the scenario to identify:
- The main situation
- The main problem or objective
- Important facts
- Conditions
- Relationships between facts
- Constraints
- Decisions or actions mentioned in the scenario

DO NOT invent information or introduce facts not present in the scenario (no new people, numbers, dates, locations, rules, policies, systems, consequences, actions, events, or relationships).
If the scenario is short, do NOT add fictional details just to make questions harder.

======================================================================
3. QUESTION VARIETY & COUNT
======================================================================
Generate a total of 5 or 6 questions.
Explore the scenario from different angles:
1. Direct understanding of explicit facts
2. Identification of the main problem / objective
3. Understanding relationships and conditions between facts
4. Application of scenario conditions
5. Reasoning based on the scenario
6. Decision-making based on the scenario

Avoid generating one question from every sentence or simply repeating the same fact.

======================================================================
4. DIFFICULTY LEVELS & DISTRIBUTION
======================================================================
Every question must have a "difficultyTag". Allowed values are ONLY:
- "Easy": Tests direct understanding of information explicitly stated in the scenario.
- "Medium": Requires connecting two or more facts or conditions from the scenario.
- "Hard": Requires deeper reasoning, application, analysis, or decision-making using only the information in the scenario.

Distribution requirements:
- If 5 questions are generated: At least 1 Easy, at least 2 Medium, and at least 1 Hard. (The 5th question can be Easy, Medium, or Hard).
- If 6 questions are generated: At least 1 Easy, at least 2 Medium, and at least 2 Hard. (The 6th question can be Easy, Medium, or Hard).

Difficulty must come from reasoning about the scenario facts, NEVER from external facts.

======================================================================
5. SUBJECT IDENTIFICATION
======================================================================
Determine the "subject" string based on the scenario domain (for example: "Database Query Logic", "Human Resources / Compensation", "Supply Chain Management", "Patient Scheduling", etc.).

======================================================================
6. OPTIONS REQUIREMENTS
======================================================================
For every question:
- "optionsList" must contain EXACTLY 4 options.
- "optionSequenceNo" must be 1, 2, 3, and 4.
- EXACTLY ONE option must have "isCorrect": true.
- EXACTLY THREE options must have "isCorrect": false.
- All 4 options must have unique, non-empty text.
- NEVER use generic options like "All of the above", "None of the above", "Both A and B", etc.
- Incorrect options (distractors) must be plausible and based on common misconceptions, reversed conditions, missing conditions, or alternative interpretations of the scenario facts.

======================================================================
7. QUESTION ID & QUESTION TYPE
======================================================================
- "questionId": Must be a unique, valid UUID v4 string (e.g. "f47ac10b-58cc-4372-a567-0e02b2c3d479").
- "questionType": Must be exactly "scenario_based".

======================================================================
8. REQUIRED JSON OUTPUT STRUCTURE
======================================================================
Return ONLY valid JSON with this exact structure and field names:

{
  "topic": "{topic}",
  "scenario": "The scenario text",
  "questions": [
    {
      "questionId": "c8e2b83d-9860-4966-bb8c-8be94f57c15e",
      "questionType": "scenario_based",
      "difficultyTag": "Easy",
      "subject": "Human Resources / Employee Filtering",
      "questionText": "What department do the employees need to work in according to the company's requirement?",
      "optionsList": [
        {
          "optionSequenceNo": 1,
          "optionText": "Marketing department",
          "isCorrect": false
        },
        {
          "optionSequenceNo": 2,
          "optionText": "Sales department",
          "isCorrect": true
        },
        {
          "optionSequenceNo": 3,
          "optionText": "Finance department",
          "isCorrect": false
        },
        {
          "optionSequenceNo": 4,
          "optionText": "Operations department",
          "isCorrect": false
        }
      ]
    }
  ]
}

======================================================================
9. FINAL CHECKLIST BEFORE RETURNING
======================================================================
- topic is present.
- scenario is present.
- questions contains exactly 5 or 6 items.
- Every question has a unique valid UUID for questionId.
- questionType is "scenario_based".
- difficultyTag is Easy, Medium, or Hard following the required distribution.
- subject is specified.
- optionsList contains 4 options with optionSequenceNo 1..4.
- Exactly 1 option isCorrect: true, 3 options isCorrect: false.
- Zero external knowledge or invented details.
- Output is ONLY raw JSON (no markdown backticks, no text before or after).

# SCENARIO (SOURCE OF TRUTH):
{scenario}"""


JSON_REPAIR_PROMPT_TEMPLATE = """The previous output failed validation with the following error:
{error_message}

Raw output was:
{raw_output}

Please fix the output to strictly conform to the closed-world scenario requirements and required JSON schema:
Topic: "{topic}"
Scenario: "{scenario}"

Remember:
1. Return ONLY valid JSON (no markdown backticks, no explanations outside JSON).
2. Exactly 5 or 6 questions in the "questions" array.
3. Exact field names: "topic", "scenario", "questions", "questionId" (valid UUID), "questionType" ("scenario_based"), "difficultyTag" ("Easy"|"Medium"|"Hard"), "subject", "questionText", "optionsList", "optionSequenceNo" (1..4), "optionText", "isCorrect" (boolean).
4. For 5 questions: >=1 Easy, >=2 Medium, >=1 Hard. For 6 questions: >=1 Easy, >=2 Medium, >=2 Hard.
5. Exactly 4 options per question, exactly 1 isCorrect: true, 3 isCorrect: false.
6. All questions, options, and explanations must be 100% grounded in the scenario with ZERO external knowledge.
"""


def format_scenario_prompt(scenario: str, topic: Optional[str] = None) -> str:
    """Formats the main user prompt with the provided scenario and optional topic."""
    t_val = (topic or "Scenario Assessment").strip()
    return (
        SCENARIO_QUESTION_USER_PROMPT
        .replace("{topic}", t_val)
        .replace("{scenario}", scenario.strip())
    )


def format_repair_prompt(scenario: str, raw_output: str, error_message: str, topic: Optional[str] = None) -> str:
    """Formats a repair prompt when validation fails."""
    t_val = (topic or "Scenario Assessment").strip()
    return (
        JSON_REPAIR_PROMPT_TEMPLATE
        .replace("{topic}", t_val)
        .replace("{scenario}", scenario.strip())
        .replace("{raw_output}", raw_output.strip())
        .replace("{error_message}", error_message.strip())
    )


# ==========================================
# 3. Topic -> 2 to 3 Scenarios Generation Prompts
# ==========================================

TOPIC_SCENARIOS_SYSTEM_PROMPT = """You are an expert scenario creator for educational assessments and problem-solving evaluations.
Your task is to create 2 to 3 distinct, realistic, and context-rich scenarios based strictly on the given topic.

# THE RULES:
1. Number of Scenarios: Generate EXACTLY 2 or 3 distinct scenarios.
2. Direct Relevance: Every scenario MUST be directly and clearly related to the given topic.
3. Distinct Situations: Each scenario must represent a completely different situation, problem, workflow, edge case, or decision-making process related to the topic. Avoid duplicate, repetitive, or overlapping situations.
4. Information Rich & Self-Contained: Describe concrete facts, conditions, rules, numerical values, or system behaviors sufficient to generate logical assessment questions. Keep each scenario concise (typically 2 to 5 clear sentences).
5. Closed-World Foundation: Each scenario serves as a self-contained, closed-world primary source of truth.
6. JSON Output: Output strictly valid JSON with exact field names: "topic" and "scenarios". In "scenarios", provide 2 or 3 objects, each with "scenarioId" (valid UUID v4) and "scenarioText". Do not include markdown fences or text outside the JSON."""


TOPIC_SCENARIOS_USER_PROMPT = """Create 2 to 3 distinct, realistic assessment scenarios based on the following topic.

Topic: {topic}

Requirements:
- Generate 2 or 3 scenarios (never fewer than 2, never more than 3).
- Each scenario must represent a distinct problem or situation related to "{topic}".
- Avoid duplicate, irrelevant, or repetitive scenarios.
- Include specific conditions, facts, constraints, and roles in each scenario.
- Keep each scenario between 2 and 5 clear sentences.
- Assign each scenario a unique UUID v4 for "scenarioId".

Return ONLY valid JSON matching this exact structure:
{{
  "topic": "{topic}",
  "scenarios": [
    {{
      "scenarioId": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "scenarioText": "First distinct scenario text..."
    }},
    {{
      "scenarioId": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
      "scenarioText": "Second distinct scenario text representing a different problem..."
    }}
  ]
}}"""


def format_topic_scenarios_prompt(topic: str) -> str:
    """Formats the prompt for generating 2-3 scenarios from a topic."""
    return TOPIC_SCENARIOS_USER_PROMPT.replace("{topic}", topic.strip())


# ==========================================
# 4. Multi-Scenario -> MCQ & MSQ Questions Prompts
# ==========================================

SCENARIOS_QUESTION_SYSTEM_PROMPT = """You are an expert assessment question generator specializing in Scenario-Based Question Generation.
Your task is to generate 5–6 questions IN TOTAL across the 2–3 SCENARIOS provided by the user.

# THE MOST IMPORTANT RULE: STRICT SCENARIO GROUNDING (CLOSED WORLD)
- The provided scenarios are the PRIMARY AND ONLY source of truth.
- Every question, option, and correct answer MUST be directly grounded in the provided scenarios.
- DO NOT invent new people, numbers, dates, locations, rules, policies, systems, consequences, actions, events, or relationships.
- DO NOT use external general knowledge or assume unmentioned facts.
- Questions must not introduce facts or assumptions that are not supported by the relevant scenario.
- Think of each scenario as a closed world.

# QUESTION FORMATS (MCQ & MSQ)
- You MUST generate both Multiple-Choice Questions (MCQ) and Multiple-Select Questions (MSQ).
- MCQ: Exactly 4 options, exactly ONE option is correct ("isCorrect": true), exactly three options are incorrect ("isCorrect": false).
- MSQ: Exactly 4 options, TWO OR MORE options are correct ("isCorrect": true), and remaining options are incorrect ("isCorrect": false). Clearly identify every correct option.

# OUTPUT REQUIREMENTS
Output strictly valid JSON matching the exact schema with exact field names and no markdown fences or outside commentary."""


SCENARIOS_QUESTION_USER_PROMPT = """You are an expert assessment question generator.

Generate a total of 5 to 6 scenario-based questions across the provided scenarios.

======================================================================
1. INPUT TOPIC & SCENARIOS
======================================================================
Topic: {topic}

Scenarios provided:
{scenarios_block}

======================================================================
2. QUESTION COUNT & DISTRIBUTION
======================================================================
- Generate ONLY 5 to 6 questions IN TOTAL across all scenarios combined (NOT 5-6 questions per scenario).
- Distribute questions across the generated scenarios appropriately: questions should cover the different scenarios provided.
- Ground each question strictly in the provided scenarios. Do not mix contradictory details.

======================================================================
3. QUESTION FORMATS: MCQ & MSQ
======================================================================
- You MUST generate BOTH "MCQ" (Multiple-Choice Question) and "MSQ" (Multiple-Select Question) formats.
- Both formats must be present in the questions list (at least one MCQ and at least one MSQ).
- Set "questionFormat" to either "MCQ" or "MSQ".
- For every question:
  - "optionsList" must contain EXACTLY 4 options with "optionSequenceNo" 1, 2, 3, 4.
  - For "MCQ": EXACTLY ONE option must have "isCorrect": true, and three have "isCorrect": false.
  - For "MSQ": TWO OR MORE options must have "isCorrect": true (e.g. 2 or 3 correct options).
  - All 4 options must have unique, non-empty text.
  - NEVER use generic options like "All of the above", "None of the above", "Both A and B".
  - Distractors must be plausible and based on the scenario facts.

======================================================================
4. DIFFICULTY LEVELS & DISTRIBUTION
======================================================================
Allowed values for "difficultyTag":
- "Easy": Direct understanding of explicit scenario facts.
- "Medium": Connecting multiple facts or conditions from the scenario.
- "Hard": Deeper reasoning, analysis, application, or decision-making.

Distribution requirements across the 5–6 questions:
- If 5 questions: At least 1 Easy, at least 2 Medium, and at least 1 Hard.
- If 6 questions: At least 1 Easy, at least 2 Medium, and at least 2 Hard.

======================================================================
5. REQUIRED JSON OUTPUT STRUCTURE
======================================================================
Return ONLY valid JSON matching this exact structure:

{{
  "topic": "{topic}",
  "scenarios": [
{scenarios_json_snippets}
  ],
  "questions": [
    {{
      "questionId": "c8e2b83d-9860-4966-bb8c-8be94f57c15e",
      "questionType": "scenario_based",
      "questionFormat": "MCQ",
      "difficultyTag": "Medium",
      "subject": "Scenario Assessment",
      "questionText": "Question based on the scenario situation.",
      "optionsList": [
        {{
          "optionSequenceNo": 1,
          "optionText": "Option A",
          "isCorrect": false
        }},
        {{
          "optionSequenceNo": 2,
          "optionText": "Option B",
          "isCorrect": true
        }},
        {{
          "optionSequenceNo": 3,
          "optionText": "Option C",
          "isCorrect": false
        }},
        {{
          "optionSequenceNo": 4,
          "optionText": "Option D",
          "isCorrect": false
        }}
      ]
    }},
    {{
      "questionId": "f1a23c4d-5678-49ab-bcde-ef0123456789",
      "questionType": "scenario_based",
      "questionFormat": "MSQ",
      "difficultyTag": "Hard",
      "subject": "Scenario Assessment",
      "questionText": "Which of the following conditions must be satisfied according to the scenario? (Select all that apply)",
      "optionsList": [
        {{
          "optionSequenceNo": 1,
          "optionText": "Condition 1 text",
          "isCorrect": true
        }},
        {{
          "optionSequenceNo": 2,
          "optionText": "Condition 2 text",
          "isCorrect": false
        }},
        {{
          "optionSequenceNo": 3,
          "optionText": "Condition 3 text",
          "isCorrect": true
        }},
        {{
          "optionSequenceNo": 4,
          "optionText": "Condition 4 text",
          "isCorrect": false
        }}
      ]
    }}
  ]
}}

======================================================================
6. FINAL CHECKLIST BEFORE RETURNING
======================================================================
- topic is present.
- scenarios array contains the input scenarios with their scenarioIds.
- questions array contains ONLY 5 or 6 questions in total across all scenarios.
- Every question has a valid UUID questionId.
- Both MCQ and MSQ question formats are present.
- MCQ has exactly 1 correct option; MSQ has 2 or more correct options.
- difficultyTag follows distribution (Easy, Medium, Hard).
- Do NOT include scenarioId or calculationDraft in question objects.
- Zero external knowledge or invented details.
- Output is ONLY raw JSON (no markdown backticks, no extra text).
"""


SCENARIOS_JSON_REPAIR_PROMPT_TEMPLATE = """The previous output failed validation with the following error:
{error_message}

Raw output was:
{raw_output}

Please fix the output to strictly conform to the closed-world scenario requirements and required JSON schema:
Topic: "{topic}"

Scenarios provided:
{scenarios_block}

Remember:
1. Return ONLY valid JSON (no markdown backticks, no explanations outside JSON).
2. Exactly 5 or 6 questions in total in the "questions" array across all scenarios.
3. Both "MCQ" and "MSQ" question formats MUST be present in the questions list.
4. For MCQ questions, exactly ONE option must have isCorrect: true.
5. For MSQ questions, TWO OR MORE options must have isCorrect: true.
6. Exactly 4 options per question with optionSequenceNo 1..4.
7. For 5 questions: >=1 Easy, >=2 Medium, >=1 Hard. For 6 questions: >=1 Easy, >=2 Medium, >=2 Hard.
8. Do NOT include scenarioId or calculationDraft in question objects.
"""


def format_scenarios_question_prompt(scenarios: list, topic: Optional[str] = None) -> str:
    """Formats the user prompt for generating questions across multiple scenarios."""
    import json
    t_val = (topic or "Scenario Assessment").strip()

    blocks = []
    snippets = []
    for i, sc in enumerate(scenarios, 1):
        sid = getattr(sc, "scenarioId", None) if hasattr(sc, "scenarioId") else sc.get("scenarioId", f"scenario-{i}")
        stext = getattr(sc, "scenarioText", None) if hasattr(sc, "scenarioText") else sc.get("scenarioText", str(sc))
        blocks.append(f"Scenario {i}:\n{stext}")
        snippet_obj = {"scenarioId": sid, "scenarioText": stext}
        snippets.append("    " + json.dumps(snippet_obj))

    scenarios_block = "\n\n".join(blocks)
    snippets_str = ",\n".join(snippets)

    return (
        SCENARIOS_QUESTION_USER_PROMPT
        .replace("{topic}", t_val)
        .replace("{scenarios_block}", scenarios_block)
        .replace("{scenarios_json_snippets}", snippets_str)
    )


def format_scenarios_repair_prompt(
    scenarios: list,
    raw_output: str,
    error_message: str,
    topic: Optional[str] = None,
) -> str:
    """Formats a repair prompt when multi-scenario validation fails."""
    t_val = (topic or "Scenario Assessment").strip()
    blocks = []
    for i, sc in enumerate(scenarios, 1):
        sid = getattr(sc, "scenarioId", None) if hasattr(sc, "scenarioId") else sc.get("scenarioId", f"scenario-{i}")
        stext = getattr(sc, "scenarioText", None) if hasattr(sc, "scenarioText") else sc.get("scenarioText", str(sc))
        blocks.append(f"Scenario {i} (scenarioId: {sid}):\n{stext}")
    scenarios_block = "\n\n".join(blocks)

    return (
        SCENARIOS_JSON_REPAIR_PROMPT_TEMPLATE
        .replace("{topic}", t_val)
        .replace("{scenarios_block}", scenarios_block)
        .replace("{raw_output}", raw_output.strip())
        .replace("{error_message}", error_message.strip())
    )

