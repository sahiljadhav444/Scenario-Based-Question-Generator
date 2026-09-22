# 🎓 Scenario-Based Question Generator

A production-grade, modular Python application that transforms any educational, business, technical, or real-world scenario into **5 to 6 high-quality multiple-choice questions** adhering strictly to closed-world grounding and rigorous JSON schema constraints.

---

## 🌟 Key Features

- **🎯 Scenario-Based Grounding (Closed World)**:
  - The scenario is the primary and only source of truth.
  - Zero external hallucinations, invented facts, or unmentioned roles/rules.
  - Generates questions exploring the scenario from varied cognitive angles: direct understanding, main problem, relationships between facts, application, reasoning, and decision-making.
- **📊 Difficulty Levels & Enforced Distribution**:
  - `Easy`, `Medium`, and `Hard` tags.
  - Enforces distribution:
    - **5 questions**: At least 1 Easy, at least 2 Medium, at least 1 Hard.
    - **6 questions**: At least 1 Easy, at least 2 Medium, at least 2 Hard.
- **🤖 Multi-Provider LLM Integration**: Built-in support for:
  - **Groq** (Ultra-fast inference with Llama 3.3 70B / Mixtral)
  - **OpenRouter** (Aggregated access to state-of-the-art models)
  - **Hugging Face** (Inference API / Serverless endpoints)
- **🔄 Intelligent Provider Fallback**: Automatic failover chain (e.g. `Groq -> OpenRouter -> Hugging Face`) when encountering rate limits (HTTP 429), server errors (5xx), or timeouts.
- **🛡️ Strict Schema Validation & Auto-Healing**:
  - Exact JSON fields: `scenario`, `questions`, `questionId` (UUID), `questionType` (`scenario_based`), `difficultyTag`, `subject`, `questionText`, `optionsList`, `optionSequenceNo`, `optionText`, `isCorrect`.
  - Exactly 4 options (`optionSequenceNo`: 1, 2, 3, 4) with exactly 1 `isCorrect: true` and 3 `isCorrect: false`.
  - Automatic self-repair prompt loop if model output deviates from the strict schema.
- **🚀 Dual Interface**:
  - **FastAPI REST API** with interactive Swagger documentation (`/docs`).
  - **CLI Terminal Mode** for direct script execution and batch processing.

---

## 📁 Project Structure

```text
scenario_question_generator/
│
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application & CLI entrypoint
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                  # Pydantic BaseSettings & environment configs
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── question_schema.py           # Pydantic V2 schemas for questions, options, & API
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── scenario_question_prompt.py  # Scenario-grounded prompt templates & repair prompts
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base_client.py               # Abstract base client interface
│   │   ├── groq_client.py               # Groq API integration
│   │   ├── huggingface_client.py        # Hugging Face API integration
│   │   ├── openrouter_client.py         # OpenRouter API integration
│   │   └── llm_manager.py               # Fallback orchestrator & provider router
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scenario_service.py          # Domain workflow coordinator
│   │   ├── question_generator.py        # Generation, validation, & auto-repair loop
│   │   └── json_validator.py            # Sanitizer, markdown stripper, & schema validator
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py                    # Loguru structured logging configuration
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py                      # FastAPI endpoint tests
│   ├── test_question_generator.py       # Generation pipeline & auto-repair tests
│   ├── test_json_validator.py           # Strict schema & edge-case validation tests
│   └── test_llm_fallback.py             # Multi-provider failover unit tests
│
├── .env                                 # Local environment variables
├── .env.example                         # Environment configuration template
├── requirements.txt                     # Production & testing dependencies
├── README.md                            # Comprehensive documentation
└── .gitignore                           # Git ignore rules
```

---

## ⚙️ Installation & Setup

### 1. Clone or Navigate to Directory
```bash
cd scenario_question_generator
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and provide your API key(s):
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Set at least one API key:
GROQ_API_KEY="your_groq_api_key_here"
OPENROUTER_API_KEY="your_openrouter_api_key_here"
HUGGINGFACE_API_KEY="your_huggingface_api_key_here"

# Optional customizations:
GROQ_MODEL="llama-3.3-70b-versatile"
OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct"
LLM_PROVIDER_ORDER="groq,openrouter,huggingface"
```

---

## 🚀 Running the Application

### Option A: Start the FastAPI Server
```bash
python -m app.main --server
```
or with Uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Interactive CLI Mode
You can generate scenario and questions directly from your terminal by providing a topic:

```bash
python -m app.main --topic "Online Shopping"
```

Specify a preferred provider:
```bash
python -m app.main --provider groq --topic "Database Management System"
```

Legacy scenario input is also supported:
```bash
python -m app.main --scenario "A hospital emergency room is implementing a triage protocol to prioritize critical patient care."
```

---

## 📡 REST API Reference

### 1. Generate Questions (Pure JSON Output)
**Endpoint**: `POST /api/v1/generate-questions`  
**Headers**: `Content-Type: application/json`

#### Request Body:
```json
{
  "topic": "Online Shopping",
  "preferred_provider": "groq",
  "temperature": 0.2
}
```

#### Response:
```json
{
  "topic": "Online Shopping",
  "scenario": "A customer orders a laptop from an online shopping website. The payment is successful, but the order confirmation does not appear.",
  "questions": [
    {
      "questionId": "c8e2b83d-9860-4966-bb8c-8be94f57c15e",
      "questionType": "scenario_based",
      "difficultyTag": "Easy",
      "subject": "Human Resources / Employee Filtering",
      "questionText": "What department do the employees need to work in?",
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
          "optionText": "Human Resources department",
          "isCorrect": false
        }
      ]
    },
    {
      "questionId": "f1a23c4d-5678-49ab-bcde-ef0123456789",
      "questionType": "scenario_based",
      "difficultyTag": "Medium",
      "subject": "Human Resources / Employee Filtering",
      "questionText": "Which two conditions must an employee satisfy to be included in the requested result?",
      "optionsList": [
        {
          "optionSequenceNo": 1,
          "optionText": "Earn more than $50,000 and work in the Sales department",
          "isCorrect": true
        },
        {
          "optionSequenceNo": 2,
          "optionText": "Earn more than $50,000 in any department",
          "isCorrect": false
        },
        {
          "optionSequenceNo": 3,
          "optionText": "Work in the Sales department with any salary",
          "isCorrect": false
        },
        {
          "optionSequenceNo": 4,
          "optionText": "Earn exactly $50,000 or work in the Sales department",
          "isCorrect": false
        }
      ]
    },
    {
      "questionId": "a9b8c7d6-e5f4-4321-ba98-76543210fedc",
      "questionType": "scenario_based",
      "difficultyTag": "Hard",
      "subject": "Human Resources / Employee Filtering",
      "questionText": "If an employee works in the Sales department but earns exactly $50,000, should that employee be included when the requirement is to find employees earning more than $50,000?",
      "optionsList": [
        {
          "optionSequenceNo": 1,
          "optionText": "Yes, because $50,000 meets the salary threshold",
          "isCorrect": false
        },
        {
          "optionSequenceNo": 2,
          "optionText": "No, because the requirement strictly specifies earning more than $50,000",
          "isCorrect": true
        },
        {
          "optionSequenceNo": 3,
          "optionText": "Yes, because the employee is in the Sales department",
          "isCorrect": false
        },
        {
          "optionSequenceNo": 4,
          "optionText": "No, because the employee is not working in Sales",
          "isCorrect": false
        }
      ]
    }
  ]
}
```

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:

```bash
pytest -v
```

---

## 📄 License

MIT License. Developed for scenario-based assessment and educational question generation.
