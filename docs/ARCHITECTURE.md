# Architecture

TestGenIQ has five layers.

1. **Input/specification** — FastAPI target and OpenAPI JSON.
2. **AI core** — LangChain orchestration, Gemini analysis and Groq generation.
3. **Test artifacts** — pytest tests and Postman collection.
4. **Validation/execution** — Schemathesis, Dredd, Newman and GitHub Actions.
5. **Intelligence/reporting** — AI RCA, coverage and unified HTML report.

The OpenAPI specification is treated as the source of truth for endpoint contracts. Generated tests must trace back to documented methods, paths, parameters, schemas and response codes.
