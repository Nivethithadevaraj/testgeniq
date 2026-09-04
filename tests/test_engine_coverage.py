import json
from pathlib import Path

from engine.contract_runner import (
    _npx_command,
    _python_command,
    _prepare_dredd_spec,
)
from engine.ingestion import (
    ingest_source_file,
    ingest_openapi_spec,
)


def test_python_command_uses_current_interpreter():
    command = _python_command("-m", "pytest")

    assert command[0]
    assert command[1:] == ["-m", "pytest"]


def test_npx_command_builds_command():
    command = _npx_command("newman", "--version")

    assert command[0]
    assert command[1] == "newman"
    assert command[2] == "--version"


def test_ingest_source_file_extracts_functions(tmp_path):
    source = '''
def first_function(name, value="test"):
    """First test function."""
    return value


async def second_function(item):
    return item
'''

    source_file = tmp_path / "sample_module.py"

    source_file.write_text(
        source,
        encoding="utf-8",
    )

    result = ingest_source_file(str(source_file))

    assert result["file"] == str(source_file)
    assert result["source"] == source
    assert len(result["functions"]) == 2

    first = result["functions"][0]
    assert first["name"] == "first_function"
    assert first["signature"] == "first_function(name, value)"
    assert first["docstring"] == "First test function."
    assert first["line"] > 0

    second = result["functions"][1]
    assert second["name"] == "second_function"
    assert second["signature"] == "second_function(item)"
    assert second["docstring"] == ""


def test_ingest_openapi_spec_skips_non_http_path_entries(tmp_path):
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Coverage Test API",
            "version": "1.0.0",
        },
        "paths": {
            "/health": {
                "get": {
                    "operationId": "health_check",
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "OK"
                        }
                    }
                },
                "parameters": [
                    {
                        "name": "ignored",
                        "in": "query",
                    }
                ],
            }
        },
    }

    spec_file = tmp_path / "openapi.json"

    spec_file.write_text(
        json.dumps(spec),
        encoding="utf-8",
    )

    result = ingest_openapi_spec(str(spec_file))

    assert len(result["operations"]) == 1
    assert result["operations"][0]["method"] == "GET"
    assert result["operations"][0]["path"] == "/health"
    assert result["operations"][0]["operation_id"] == "health_check"


def test_ingest_openapi_spec_reads_valid_spec(tmp_path):
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Coverage Test API",
            "version": "1.0.0",
        },
        "paths": {
            "/health": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "OK"
                        }
                    }
                }
            }
        },
    }

    spec_file = tmp_path / "openapi.json"

    spec_file.write_text(
        json.dumps(spec),
        encoding="utf-8",
    )

    result = ingest_openapi_spec(str(spec_file))

    assert result is not None
    assert len(result["operations"]) == 1


def test_prepare_dredd_spec_creates_compatible_copy():
    target = _prepare_dredd_spec()

    assert Path(target).exists()

    data = json.loads(
        Path(target).read_text(
            encoding="utf-8"
        )
    )

    assert data["openapi"] == "3.0.3"
    assert "paths" in data
    assert len(data["paths"]) > 0