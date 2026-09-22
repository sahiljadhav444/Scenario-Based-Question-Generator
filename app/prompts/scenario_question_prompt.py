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
