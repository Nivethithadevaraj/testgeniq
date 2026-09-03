# TestGenIQ — Intelligent API Test Generation & Validation

## Business use case
TestGenIQ automates the API quality lifecycle: OpenAPI ingestion → LangChain orchestration → Gemini scenario analysis → Groq assertion/test generation → Postman collection → Schemathesis/Dredd contract validation → Newman execution → CI/CD → AI failure RCA → unified HTML reporting.

## Target application
A lightweight FastAPI Task Manager with two modules:
1. `app/tasks.py` — task CRUD and validation
2. `app/auth.py` — registration, login, user lookup and deactivation

## Pipeline
```text
FastAPI Target
     ↓
/openapi.json
     ↓
OpenAPI ingestion
     ↓
LangChain
     ├── Gemini → scenario analysis
     └── Groq   → executable test/assertion generation
     ↓
Postman Collection JSON
     ├── Schemathesis
     └── Dredd
     ↓
Newman
     ↓
GitHub Actions
     ↓
AI RCA + HTML report + coverage
```

## Local run
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
uvicorn app.main:app --reload
```

In another terminal:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/openapi.json | ConvertTo-Json -Depth 100 | Set-Content openapi.json -Encoding utf8
python generate_tests.py
python run_testgeniq.py
```

## AI configuration
Copy `.env.example` to `.env` and add keys locally. Never commit `.env`.

The architecture uses Gemini for long-context analysis and Groq for fast generation. Model names are configurable because provider availability changes; do not hard-code an inaccessible model.

## QA acceptance targets
- 20+ generated tests
- positive, negative and edge categories
- 2 target modules
- executable pytest/Postman/E2E evidence
- ≥80% engine coverage
- contract validation
- CI execution
- 3+ distinct AI RCA scenarios
- complete evidence pack and Moodle documentation

## Important contract-testing note
Schemathesis is the primary OpenAPI 3 contract/property testing engine. Dredd is retained as the second validator through a generated OpenAPI 2 compatibility description because Dredd's OpenAPI 3 support is limited/experimental.

## Security
API keys are environment secrets only. GitHub secrets should be named `GEMINI_API_KEY` and `GROQ_API_KEY`. Do not paste keys into source, screenshots, README, or commit history.
