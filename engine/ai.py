from __future__ import annotations

import os
import re

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_with_gemini(
    prompt: str,
) -> str:
    """
    Use Gemini to analyze the supplied source code,
    OpenAPI contract and requested test scenarios.

    Gemini is used for analysis/reasoning only.
    """

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    model = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0,
    )

    response = model.invoke(
        f"""
You are TestGenIQ's API test-analysis engine.

Analyze the following source material.

Your analysis MUST:

1. Identify the actual public functions.
2. Identify their exact parameters.
3. Identify valid inputs.
4. Identify invalid inputs.
5. Identify actual exceptions.
6. Identify actual return values.
7. Identify edge cases supported by the implementation.
8. Cross-check the OpenAPI contract.
9. Never invent behavior.

SOURCE MATERIAL
===============

{prompt}

Return a concise structured analysis for a second AI
model that will generate pytest code.
"""
    )

    content = getattr(
        response,
        "content",
        str(response),
    )

    return str(content)


# ============================================================
# GROQ CODE GENERATION
# ============================================================

def generate_with_groq(
    prompt: str,
) -> str:
    """
    Use Groq through LangChain to generate pytest code.
    """

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    from langchain_groq import ChatGroq

    model = ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=0,
        max_tokens=2500,
    )

    response = model.invoke(
        f"""
Generate executable pytest Python source for TestGenIQ.

TARGET:
{prompt}

RULES:
- Use only functions and behavior stated in the target.
- Generate positive, negative, and edge-case tests.
- Use pytest.
- Use only real imports.
- Do not invent functions, parameters, fields, exceptions, or behavior.
- Return Python source only.
- Do not use Markdown fences.
- Include comments containing:
  POSITIVE SCENARIO
  NEGATIVE SCENARIO
  EDGE CASE
"""
    )

    content = getattr(
        response,
        "content",
        str(response),
    )

    return str(content)
# ============================================================
# GENERATED CODE CLEANUP
# ============================================================

def _clean_generated_code(
    code: str,
) -> str:

    code = code.strip()

    code = re.sub(
        r"^```(?:python)?\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"\s*```$",
        "",
        code,
    )

    return code.strip()

# ============================================================
# TEST GENERATION PIPELINE
# ============================================================

def generate_test_code(
    prompt: str,
    module_name: str = "api",
) -> str:
    """
    Generate executable pytest code using:

        Gemini -> analysis
        Groq   -> code generation

    The original source/context is supplied to Gemini first.
    Only Gemini's analysis is passed to Groq to avoid
    duplicating the full source/OpenAPI payload.
    """

    analysis = analyze_with_gemini(
        prompt
    )

    # Keep the Groq request comfortably below the model's
    # context/request limit while preserving the useful
    # Gemini analysis.
    analysis = str(analysis).strip()

    if len(analysis) > 16000:
        analysis = analysis[:16000]

    generation_prompt = f"""
TARGET MODULE
=============

{module_name}

GEMINI SOURCE ANALYSIS
======================

{analysis}

Generate executable pytest code now.

Remember:
- Use only functions and signatures identified in the analysis.
- Use only behavior supported by the source.
- Include positive, negative and edge scenarios.
- Use pytest fixtures where appropriate.
- Return Python source only.
- Do not use Markdown fences.
"""

    generated = generate_with_groq(
        generation_prompt
    )

    return _clean_generated_code(
        generated
    )


# ============================================================
# AI FAILURE EXPLANATION
# ============================================================

def explain_failure_with_gemini(
    evidence: str,
) -> str:
    """
    Explain test failures using Gemini.

    A deterministic fallback is returned if Gemini
    is unavailable or rate-limited.
    """

    if not GEMINI_API_KEY:
        return deterministic_failure_explanation(
            evidence
        )

    try:

        from langchain_google_genai import (
            ChatGoogleGenerativeAI
        )

        model = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0,
        )

        response = model.invoke(
            f"""
You are TestGenIQ's failure-analysis engine.

Analyze this API testing evidence.

Identify:

1. Failure category
2. Likely root cause
3. Evidence
4. Recommended remediation
5. Whether the issue is an application defect,
   contract mismatch, test-data issue, or tooling issue.

Do not invent information.

FAILURE EVIDENCE
================

{evidence}
"""
        )

        content = getattr(
            response,
            "content",
            str(response),
        )

        return str(content)

    except Exception:
        return deterministic_failure_explanation(
            evidence
        )


def deterministic_failure_explanation(
    evidence: str,
) -> str:

    text = evidence.lower()

    if "404" in text:
        return (
            "Failure category: Test-data/resource mismatch.\n"
            "Likely root cause: The requested resource does "
            "not exist in the in-memory application state.\n"
            "Evidence: The execution output contains HTTP 404.\n"
            "Recommended remediation: Seed the required "
            "resource before state-dependent contract tests."
        )

    if "422" in text:
        return (
            "Failure category: Validation/contract mismatch.\n"
            "Likely root cause: Generated input does not satisfy "
            "the API validation contract or expected schema.\n"
            "Evidence: The execution output contains HTTP 422.\n"
            "Recommended remediation: Compare generated input "
            "with the OpenAPI request schema."
        )

    if "500" in text:
        return (
            "Failure category: Server error.\n"
            "Likely root cause: The API raised an unexpected "
            "internal exception.\n"
            "Evidence: The execution output contains HTTP 500.\n"
            "Recommended remediation: Inspect application logs "
            "and reproduce the failing request."
        )

    return (
        "Failure category: Test execution/contract mismatch.\n"
        "Root cause requires inspection of the supplied "
        "execution evidence.\n"
        "Recommended remediation: Compare expected and actual "
        "HTTP status, response body and contract definition."
    )


def classify_failure(
    evidence: str,
) -> str:

    text = evidence.lower()

    if "500" in text:
        return "server_error"

    if "422" in text:
        return "validation_or_schema_mismatch"

    if "404" in text:
        return "missing_resource_or_test_data"

    if "allow header" in text:
        return "http_contract_header_mismatch"

    if "undocumented" in text:
        return "undocumented_status_code"

    if "network error" in text:
        return "network_or_environment_error"

    return "contract_or_test_execution_failure"