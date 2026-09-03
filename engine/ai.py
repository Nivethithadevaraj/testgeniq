from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# HELPERS
# ============================================================

def _langchain_available():
    try:
        import langchain_core
        return True
    except Exception:
        return False


def _safe_text(content) -> str:
    """
    Convert a LangChain response into plain text.
    """

    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                parts.append(
                    str(item.get("text", item))
                )
            else:
                parts.append(str(item))

        return "\n".join(parts)

    return str(content)


def _invoke(model, system: str, human: str) -> str:
    """
    Invoke a LangChain chat model.
    """

    from langchain_core.messages import (
        SystemMessage,
        HumanMessage,
    )

    response = model.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=human),
        ]
    )

    return _safe_text(response.content)


# ============================================================
# GEMINI
# ============================================================

def _build_gemini():
    from langchain_google_genai import (
        ChatGoogleGenerativeAI,
    )

    return ChatGoogleGenerativeAI(
        model=os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        ),
        google_api_key=os.getenv(
            "GEMINI_API_KEY"
        ),
        temperature=0.1,
    )


# ============================================================
# GROQ
# ============================================================

def _build_groq():
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        ),
        groq_api_key=os.getenv(
            "GROQ_API_KEY"
        ),
        temperature=0.1,
    )


# ============================================================
# GEMINI - OPENAPI ANALYSIS
# ============================================================

def analyze_with_gemini(context: str) -> str:
    """
    Analyze an OpenAPI/API context and identify:

    - positive scenarios
    - negative scenarios
    - boundary cases
    - expected status codes
    - assertions
    - dependencies
    """

    if not os.getenv("GEMINI_API_KEY"):
        return (
            "AI analysis unavailable; "
            "deterministic scenario planner used."
        )

    if not _langchain_available():
        return (
            "LangChain unavailable; "
            "deterministic scenario planner used."
        )

    system = """
You are the TestGenIQ API Test Architect.

Analyze the supplied OpenAPI specification and source context.

Identify:

1. Positive test scenarios
2. Negative test scenarios
3. Boundary and edge cases
4. Required parameters
5. Optional parameters
6. Expected HTTP status codes
7. Response assertions
8. Validation behavior
9. Resource dependencies
10. Authentication behavior when applicable

STRICT RULES:

- Use ONLY information present in the supplied context.
- Never invent endpoints.
- Never invent request fields.
- Never invent response fields.
- Never invent undocumented status codes.
- Never invent authentication mechanisms.
- Clearly distinguish documented behavior from inferred scenarios.
- Prefer deterministic, executable test ideas.
- Include endpoint, method, input condition,
  expected result, and assertions.
"""

    try:
        return _invoke(
            _build_gemini(),
            system,
            context,
        )

    except Exception as exc:
        return (
            "Gemini analysis failed gracefully. "
            f"Reason: {type(exc).__name__}. "
            "Deterministic scenario planner used."
        )


# ============================================================
# GROQ - TEST GENERATION
# ============================================================

def generate_with_groq(context: str) -> str:
    """
    Generate executable API test scenarios.
    """

    if not os.getenv("GROQ_API_KEY"):
        return (
            "AI generation unavailable; "
            "deterministic generator used."
        )

    if not _langchain_available():
        return (
            "LangChain unavailable; "
            "deterministic generator used."
        )

    system = """
You are TestGenIQ's executable API test generation engine.

Generate practical API test scenarios using ONLY
the supplied context.

Cover:

- Positive tests
- Negative tests
- Validation tests
- Boundary tests
- Error handling
- HTTP status assertions
- Response assertions

STRICT RULES:

- Do not invent endpoints.
- Do not invent request fields.
- Do not invent response fields.
- Do not invent undocumented status codes.
- Do not assume authentication if it is not documented.
- Use the supplied OpenAPI/source context as truth.
- Prefer deterministic test data.
- Tests must be suitable for pytest or Postman.
- Keep the output concise and structured.
"""

    try:
        return _invoke(
            _build_groq(),
            system,
            context,
        )

    except Exception as exc:
        return (
            "Groq generation failed gracefully. "
            f"Reason: {type(exc).__name__}. "
            "Deterministic generator used."
        )


# ============================================================
# FAILURE CLASSIFICATION
# ============================================================

def classify_failure(failure_text: str) -> str:
    """
    Deterministically classify a failure.

    This is used before AI RCA so that the report still
    contains useful information if an AI provider is unavailable.
    """

    text = (failure_text or "").lower()

    if "timeout" in text:
        return "TIMEOUT / AVAILABILITY"

    if "connection refused" in text:
        return "SERVICE UNAVAILABLE"

    if "connection error" in text:
        return "NETWORK / SERVICE ERROR"

    if "404" in text or "not found" in text:
        return "RESOURCE / STATE MISMATCH"

    if "400" in text or "bad request" in text:
        return "REQUEST VALIDATION"

    if "401" in text or "unauthorized" in text:
        return "AUTHENTICATION"

    if "403" in text or "forbidden" in text:
        return "AUTHORIZATION"

    if "422" in text or "validation" in text:
        return "SCHEMA / VALIDATION"

    if "500" in text or "internal server error" in text:
        return "SERVER ERROR"

    if "allow header" in text:
        return "HTTP HEADER / CONTRACT"

    if "schema" in text:
        return "CONTRACT / RESPONSE SCHEMA"

    if "status code" in text:
        return "CONTRACT / STATUS CODE"

    if "dredd" in text:
        return "DREDD CONTRACT VALIDATION"

    if "schemathesis" in text:
        return "SCHEMATHESIS CONTRACT VALIDATION"

    return "UNKNOWN / REQUIRES INVESTIGATION"


# ============================================================
# DETERMINISTIC RCA
# ============================================================

def _deterministic_rca(failure_text: str) -> str:
    """
    Produce RCA without requiring an AI provider.
    """

    category = classify_failure(failure_text)

    if category == "RESOURCE / STATE MISMATCH":

        explanation = (
            "The request reached the target API, but the "
            "expected resource was not present in the current "
            "application state."
        )

        action = (
            "Seed the required resource before the dependent "
            "test, or explicitly model the resource dependency."
        )

    elif category == "CONTRACT / STATUS CODE":

        explanation = (
            "The actual HTTP status returned by the API does "
            "not match the status documented or expected by "
            "the contract test."
        )

        action = (
            "Compare the OpenAPI response definitions with "
            "actual endpoint behavior and correct the API "
            "contract or implementation."
        )

    elif category == "SCHEMA / VALIDATION":

        explanation = (
            "The generated request or API response did not "
            "satisfy the schema or validation constraints."
        )

        action = (
            "Compare the generated payload and API schema "
            "field by field and correct the generator, "
            "schema, or endpoint validation."
        )

    elif category == "HTTP HEADER / CONTRACT":

        explanation = (
            "The API response headers do not match the "
            "headers required by the contract."
        )

        action = (
            "Review the documented response headers and "
            "verify the API response."
        )

    elif category == "SERVICE UNAVAILABLE":

        explanation = (
            "The test could not establish a connection "
            "to the target service."
        )

        action = (
            "Verify that the FastAPI service is running "
            "and that the configured target URL is reachable."
        )

    elif category == "TIMEOUT / AVAILABILITY":

        explanation = (
            "The request exceeded the configured execution "
            "timeout."
        )

        action = (
            "Check service responsiveness, dependency latency, "
            "and timeout configuration."
        )

    else:

        explanation = (
            "The recorded execution output indicates a "
            "failure requiring comparison of expected and "
            "actual behavior."
        )

        action = (
            "Inspect the complete tool log and reproduce "
            "the failing scenario independently."
        )

    return (
        f"Failure category: {category}\n\n"
        f"Root cause assessment: {explanation}\n\n"
        f"Recommended corrective action: {action}\n\n"
        "Evidence basis: recorded test execution output only."
    )


# ============================================================
# GEMINI - FAILURE RCA
# ============================================================

def explain_failure_with_gemini(
    failure_text: str,
) -> str:
    """
    Generate AI-assisted root cause analysis.

    Falls back to deterministic RCA if Gemini is unavailable.
    """

    deterministic = _deterministic_rca(
        failure_text
    )

    if not os.getenv("GEMINI_API_KEY"):
        return deterministic

    if not _langchain_available():
        return deterministic

    category = classify_failure(
        failure_text
    )

    system = """
You are TestGenIQ's Senior SDET Root Cause Analysis assistant.

Analyze ONLY the supplied test execution evidence.

Return:

FAILURE CATEGORY:
ROOT CAUSE:
EVIDENCE:
CONTRACT IMPACT:
AFFECTED COMPONENT:
CONFIDENCE:
CORRECTIVE ACTION:

Rules:

- Do not invent facts.
- Do not claim unsupported root causes.
- Distinguish confirmed evidence from likely causes.
- If evidence is insufficient, explicitly say so.
- Focus on actionable QA/SDET analysis.
"""

    human = (
        f"Deterministic failure category: {category}\n\n"
        "Recorded execution evidence:\n"
        f"{failure_text[:12000]}"
    )

    try:

        result = _invoke(
            _build_gemini(),
            system,
            human,
        )

        if result.strip():
            return result

    except Exception:
        pass

    return deterministic