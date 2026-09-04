from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import engine.ai as ai
import engine.api_generator as api_generator
import engine.contract_runner as contract_runner
import engine.reporting as reporting

from engine.ingestion import (
    ingest_openapi_spec,
)


# ============================================================
# INGESTION
# ============================================================

def test_ingest_openapi_spec(tmp_path):

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Test API",
            "version": "1.0",
        },
        "paths": {
            "/health": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "OK",
                        }
                    }
                }
            }
        },
    }

    path = (
        tmp_path
        / "openapi.json"
    )

    path.write_text(
        json.dumps(spec),
        encoding="utf-8",
    )

    result = ingest_openapi_spec(
        str(path)
    )

    assert result["openapi"] == "3.1.0"
    assert result["info"]["title"] == "Test API"
    assert "/health" in result["paths"]


# ============================================================
# API GENERATOR
# ============================================================

def test_build_collection_contains_all_scenarios():

    collection = (
        api_generator.build_collection(
            {
                "info": {
                    "title": "Target API",
                }
            }
        )
    )

    names = [
        item["name"]
        for item in collection["item"]
    ]

    assert any(
        "[POSITIVE]" in name
        for name in names
    )

    assert any(
        "[NEGATIVE]" in name
        for name in names
    )

    assert any(
        "[EDGE_CASE]" in name
        for name in names
    )

    assert len(names) >= 15


def test_generate_postman_collection(
    tmp_path,
):

    source = (
        tmp_path
        / "openapi.json"
    )

    source.write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "info": {
                    "title": "Target",
                    "version": "1",
                },
                "paths": {},
            }
        ),
        encoding="utf-8",
    )

    output = (
        tmp_path
        / "generated.json"
    )

    result = (
        api_generator
        .generate_postman_collection(
            source,
            output,
        )
    )

    assert result == output
    assert output.exists()

    payload = json.loads(
        output.read_text(
            encoding="utf-8"
        )
    )

    assert (
        payload["info"]["name"]
        == "TestGenIQ Generated Collection"
    )

    serialized = json.dumps(
        payload
    )

    assert "EDGE_CASE" in serialized


def test_generate_postman_collection_missing_file(
    tmp_path,
):

    with pytest.raises(
        FileNotFoundError
    ):
        (
            api_generator
            .generate_postman_collection(
                tmp_path / "missing.json",
                tmp_path / "out.json",
            )
        )


# ============================================================
# AI HELPERS
# ============================================================

def test_clean_generated_code():

    source = (
        "```python\n"
        "import pytest\n\n"
        "def test_ok():\n"
        "    assert True\n"
        "```"
    )

    cleaned = (
        ai._clean_generated_code(
            source
        )
    )

    assert "```" not in cleaned
    assert "def test_ok" in cleaned


def test_classify_failure():

    assert (
        ai.classify_failure(
            "HTTP 500 internal server error"
        )
        == "server_error"
    )

    assert (
        ai.classify_failure(
            "HTTP 422 validation"
        )
        == "validation_or_schema_mismatch"
    )

    assert (
        ai.classify_failure(
            "404 resource missing"
        )
        == "missing_resource_or_test_data"
    )

    assert (
        ai.classify_failure(
            "Invalid Allow header"
        )
        == "http_contract_header_mismatch"
    )

    assert (
        ai.classify_failure(
            "undocumented response"
        )
        == "undocumented_status_code"
    )

    assert (
        ai.classify_failure(
            "network error"
        )
        == "network_or_environment_error"
    )

    assert (
        ai.classify_failure(
            "some unknown failure"
        )
        == "contract_or_test_execution_failure"
    )


@pytest.mark.parametrize(
    "evidence, expected",
    [
        (
            "404 Not Found",
            "Test-data/resource mismatch",
        ),
        (
            "422 validation",
            "Validation/contract mismatch",
        ),
        (
            "500 Internal Server Error",
            "Server error",
        ),
        (
            "unknown",
            "Test execution/contract mismatch",
        ),
    ],
)
def test_deterministic_failure_explanation(
    evidence,
    expected,
):

    result = (
        ai.deterministic_failure_explanation(
            evidence
        )
    )

    assert expected in result


class FakeModel:

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        pass

    def invoke(
        self,
        prompt,
    ):

        if "analysis engine" in prompt.lower():
            return SimpleNamespace(
                content=(
                    "Use only actual functions and "
                    "actual source behavior."
                )
            )

        if "pytest" in prompt.lower():
            return SimpleNamespace(
                content=(
                    "```python\n"
                    "import pytest\n\n"
                    "# POSITIVE SCENARIO\n"
                    "def test_generated():\n"
                    "    assert True\n"
                    "```"
                )
            )

        return SimpleNamespace(
            content="AI RCA explanation"
        )


def test_ai_generation_without_real_network(
    monkeypatch,
):

    import langchain_google_genai
    import langchain_groq

    monkeypatch.setattr(
        langchain_google_genai,
        "ChatGoogleGenerativeAI",
        FakeModel,
    )

    monkeypatch.setattr(
        langchain_groq,
        "ChatGroq",
        FakeModel,
    )

    monkeypatch.setattr(
        ai,
        "GEMINI_API_KEY",
        "fake-key",
    )

    monkeypatch.setattr(
        ai,
        "GROQ_API_KEY",
        "fake-key",
    )

    analysis = (
        ai.analyze_with_gemini(
            "source"
        )
    )

    assert "actual functions" in analysis

    generated = (
        ai.generate_with_groq(
            "pytest generation"
        )
    )

    assert "test_generated" in generated

    final = ai.generate_test_code(
        "source",
        "tasks",
    )

    assert "```" not in final
    assert "test_generated" in final


def test_ai_failure_explanation_with_mock(
    monkeypatch,
):

    import langchain_google_genai

    monkeypatch.setattr(
        langchain_google_genai,
        "ChatGoogleGenerativeAI",
        FakeModel,
    )

    monkeypatch.setattr(
        ai,
        "GEMINI_API_KEY",
        "fake-key",
    )

    result = (
        ai.explain_failure_with_gemini(
            "failure evidence"
        )
    )

    assert result


def test_ai_failure_fallback_when_no_key(
    monkeypatch,
):

    monkeypatch.setattr(
        ai,
        "GEMINI_API_KEY",
        None,
    )

    result = (
        ai.explain_failure_with_gemini(
            "404 not found"
        )
    )

    assert (
        "Test-data/resource mismatch"
        in result
    )


# ============================================================
# CONTRACT RUNNER HELPERS
# ============================================================

def test_python_command():

    command = (
        contract_runner._python_command(
            "-m",
            "pytest",
        )
    )

    assert (
        command[0]
        == sys.executable
    )

    assert "-m" in command


def test_npx_command(
    monkeypatch,
):

    monkeypatch.setattr(
        contract_runner.shutil,
        "which",
        lambda name: (
            "npx.cmd"
            if name == "npx.cmd"
            else None
        ),
    )

    command = (
        contract_runner._npx_command(
            "newman",
            "--version",
        )
    )

    assert command == [
        "npx.cmd",
        "newman",
        "--version",
    ]


def test_npx_command_missing(
    monkeypatch,
):

    monkeypatch.setattr(
        contract_runner.shutil,
        "which",
        lambda name: None,
    )

    with pytest.raises(
        FileNotFoundError
    ):
        contract_runner._npx_command(
            "newman"
        )


def test_run_command(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        contract_runner,
        "ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        contract_runner,
        "ARTIFACTS",
        tmp_path,
    )

    result = contract_runner._run(
        [
            sys.executable,
            "-c",
            "print('engine coverage test')",
        ],
        "runner.log",
    )

    assert result["passed"] is True
    assert result["return_code"] == 0

    assert (
        tmp_path
        / "runner.log"
    ).exists()


def test_prepare_dredd_spec(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        contract_runner,
        "ROOT",
        tmp_path,
    )

    artifacts = (
        tmp_path
        / "artifacts"
    )

    artifacts.mkdir()

    monkeypatch.setattr(
        contract_runner,
        "ARTIFACTS",
        artifacts,
    )

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "API",
            "version": "1",
        },
        "paths": {
            "/tasks/{task_id}": {
                "get": {
                    "parameters": [
                        {
                            "name": "task_id",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "integer",
                                "examples": [1],
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                        }
                    },
                }
            },

            "/users/{username}": {
                "get": {
                    "parameters": [
                        {
                            "name": "username",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                        }
                    },
                }
            },
        },
    }

    (
        tmp_path
        / "openapi.json"
    ).write_text(
        json.dumps(spec),
        encoding="utf-8",
    )

    result = (
        contract_runner
        ._prepare_dredd_spec()
    )

    assert result.exists()

    converted = json.loads(
        result.read_text(
            encoding="utf-8"
        )
    )

    assert (
        converted["openapi"]
        == "3.0.3"
    )

    task_parameter = (
        converted["paths"]
        ["/tasks/{task_id}"]
        ["get"]
        ["parameters"][0]
    )

    assert (
        task_parameter["example"]
        == 1
    )

    username_parameter = (
        converted["paths"]
        ["/users/{username}"]
        ["get"]
        ["parameters"][0]
    )

    assert (
        username_parameter["example"]
        == "testuser"
    )


def test_contract_runner_orchestration(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        contract_runner,
        "ARTIFACTS",
        tmp_path,
    )

    fake_spec = (
        tmp_path
        / "openapi_dredd.json"
    )

    fake_spec.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        contract_runner,
        "_prepare_dredd_spec",
        lambda: fake_spec,
    )

    monkeypatch.setattr(
        contract_runner,
        "_npx_command",
        lambda package, *args: [
            package,
            *args,
        ],
    )

    monkeypatch.setattr(
        contract_runner.shutil,
        "which",
        lambda name: "st",
    )

    def fake_run(
        command,
        log_name,
    ):

        return {
            "command": command,
            "return_code": 0,
            "passed": True,
            "available": True,
            "stdout": "PASS",
            "stderr": "",
            "log": str(
                tmp_path
                / log_name
            ),
        }

    monkeypatch.setattr(
        contract_runner,
        "_run",
        fake_run,
    )

    results = (
        contract_runner
        .run_all_contract_tests()
    )

    assert "pytest" in results
    assert "schemathesis" in results
    assert "dredd" in results
    assert "newman" in results
    assert "playwright" in results

    assert all(
        result["passed"]
        for result in results.values()
    )

    assert (
        tmp_path
        / "contract-results.json"
    ).exists()


# ============================================================
# REPORTING
# ============================================================

def test_reporting_builds_html(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        reporting,
        "ARTIFACTS",
        tmp_path,
    )

    monkeypatch.setattr(
        reporting,
        "explain_failure_with_gemini",
        lambda evidence: (
            "Mocked AI root cause"
        ),
    )

    results = {
        "pytest": {
            "passed": True,
            "available": True,
            "return_code": 0,
            "stdout": "39 passed",
            "stderr": "",
            "log": "pytest.log",
        },

        "schemathesis": {
            "passed": False,
            "available": True,
            "return_code": 1,
            "stdout": "422 validation failure",
            "stderr": "",
            "log": "schemathesis.log",
        },
    }

    output = (
        tmp_path
        / "report.html"
    )

    result = (
        reporting.build_report(
            results,
            output,
        )
    )

    assert result.exists()

    content = result.read_text(
        encoding="utf-8"
    )

    assert (
        "TestGenIQ Unified Test Report"
        in content
    )

    assert "AI Failure Intelligence" in content

    assert "Mocked AI root cause" in content


def test_reporting_aliases(
    tmp_path,
):

    results = {
        "pytest": {
            "passed": True,
            "available": True,
            "return_code": 0,
            "stdout": "",
            "stderr": "",
            "log": None,
        }
    }

    result1 = (
        reporting.generate_report(
            results,
            tmp_path / "a.html",
        )
    )

    result2 = (
        reporting.generate_html_report(
            results,
            tmp_path / "b.html",
        )
    )

    assert result1.exists()
    assert result2.exists()