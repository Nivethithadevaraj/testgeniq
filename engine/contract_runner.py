import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def _run(command, log_name):
    """
    Execute a command safely and store its output as an artifact.
    """
    env = os.environ.copy()

    # Force UTF-8 output on Windows.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        shell=False,
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    log_path = ARTIFACTS / log_name

    log_path.write_text(
        stdout + "\n" + stderr,
        encoding="utf-8",
    )

    return {
        "command": command,
        "return_code": result.returncode,
        "passed": result.returncode == 0,
        "available": True,
        "stdout": stdout[-5000:],
        "stderr": stderr[-5000:],
        "log": str(log_path),
    }


def _npx_command(package_name, *args):
    """
    Windows-safe command builder for npm packages.

    Uses npx.cmd on Windows when available.
    """
    npx = shutil.which("npx.cmd") or shutil.which("npx")

    if not npx:
        raise FileNotFoundError(
            "npx was not found. Make sure Node.js is installed "
            "and available on PATH."
        )

    return [npx, package_name, *args]


def _python_command(*args):
    """
    Use the currently active Python interpreter.
    """
    return [sys.executable, *args]


def _prepare_dredd_spec():
    """
    Prepare a Dredd-compatible copy of the authoritative OpenAPI spec.

    The main openapi.json remains unchanged and is used by:
        - AI generation
        - Schemathesis

    Dredd receives a compatibility copy because Dredd's OpenAPI 3.x
    support is more limited than the authoritative OpenAPI 3.1 document.

    Transformations:
        1. OpenAPI 3.1 -> 3.0.3 compatibility version.
        2. Move path parameter examples to parameter-level `example`.
        3. Remove nested schema-level `examples` from path parameters.
        4. Preserve the rest of the contract.
    """

    source = ROOT / "openapi.json"
    target = ARTIFACTS / "openapi_dredd.json"

    if not source.exists():
        raise FileNotFoundError(
            f"OpenAPI specification not found: {source}"
        )

    # utf-8-sig safely handles both BOM and non-BOM JSON.
    data = json.loads(
        source.read_text(encoding="utf-8-sig")
    )

    # Work on a copy so the source specification is never modified.
    dredd_data = copy.deepcopy(data)

    # ---------------------------------------------------------
    # OpenAPI version compatibility
    # ---------------------------------------------------------
    #
    # Dredd has limited OpenAPI 3.1 support.
    # The target API itself remains OpenAPI 3.1.
    #
    # This compatibility artifact declares 3.0.3.
    #
    if dredd_data.get("openapi", "").startswith("3."):
        dredd_data["openapi"] = "3.0.3"

    # ---------------------------------------------------------
    # Path parameter compatibility
    # ---------------------------------------------------------
    #
    # FastAPI may produce:
    #
    # "schema": {
    #     "type": "integer",
    #     "examples": [1]
    # }
    #
    # Dredd expects:
    #
    # "example": 1
    #
    for path, path_item in dredd_data.get("paths", {}).items():

        if not isinstance(path_item, dict):
            continue

        for operation_name, operation in path_item.items():

            if operation_name.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
                "trace",
            }:
                continue

            if not isinstance(operation, dict):
                continue

            parameters = operation.get("parameters", [])

            if not isinstance(parameters, list):
                continue

            for parameter in parameters:

                if not isinstance(parameter, dict):
                    continue

                if parameter.get("in") != "path":
                    continue

                name = parameter.get("name")
                schema = parameter.get("schema")

                # -------------------------------------------------
                # task_id
                # -------------------------------------------------
                if name == "task_id":
                    parameter["example"] = 1

                # -------------------------------------------------
                # username
                # -------------------------------------------------
                elif name == "username":
                    parameter["example"] = "testuser"

                # -------------------------------------------------
                # Generic fallback
                # -------------------------------------------------
                elif "example" not in parameter:

                    if isinstance(schema, dict):

                        examples = schema.get("examples")

                        if isinstance(examples, list) and examples:
                            parameter["example"] = examples[0]

                        elif "example" in schema:
                            parameter["example"] = schema["example"]

                        elif schema.get("type") == "integer":
                            parameter["example"] = 1

                        elif schema.get("type") == "number":
                            parameter["example"] = 1

                        elif schema.get("type") == "string":
                            parameter["example"] = "test"

                # -------------------------------------------------
                # Remove schema-level examples from path parameters.
                # Dredd expects the example directly on the parameter.
                # -------------------------------------------------
                if isinstance(schema, dict):
                    schema.pop("examples", None)

    # ---------------------------------------------------------
    # Write compatibility artifact WITHOUT BOM
    # ---------------------------------------------------------
    target.write_text(
        json.dumps(
            dredd_data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return target


def run_all_contract_tests():
    """
    Execute the complete TestGenIQ validation stack:

        1. pytest
        2. Schemathesis
        3. Dredd
        4. Newman
        5. Playwright

    Results are written to:
        artifacts/contract-results.json
    """

    results = {}

    # =========================================================
    # 1. PYTEST
    # =========================================================

    pytest_cmd = _python_command(
        "-m",
        "pytest",
        "tests",
        "--cov=engine",
        "--cov-report=term-missing",
        "--cov-report=html:artifacts/htmlcov",
    )

    results["pytest"] = _run(
        pytest_cmd,
        "pytest.log",
    )

    # =========================================================
    # 2. SCHEMATHESIS
    # =========================================================

    st_exe = (
        shutil.which("st.exe")
        or shutil.which("st")
    )

    if st_exe:

        schemathesis_cmd = [
            st_exe,
            "run",
            "openapi.json",
            "--url",
            "http://127.0.0.1:8000",
            "--mode",
            "all",
            "--phases",
            "examples,coverage,fuzzing",
            "--max-examples",
            "5",
            "--continue-on-failure",
            "--no-color",
        ]

        results["schemathesis"] = _run(
            schemathesis_cmd,
            "schemathesis.log",
        )

    else:

        results["schemathesis"] = {
            "command": ["st"],
            "return_code": None,
            "passed": False,
            "available": False,
            "stdout": "",
            "stderr": (
                "Schemathesis executable 'st' was not found."
            ),
            "log": None,
        }

    # =========================================================
    # 3. DREDD
    # =========================================================

    try:

        # Automatically create Dredd compatibility specification.
        dredd_spec = _prepare_dredd_spec()

        dredd_cmd = _npx_command(
            "dredd",
            str(dredd_spec),
            "http://127.0.0.1:8000",
            "--hookfiles",
            "scripts/dredd_hooks.js",
            "--reporter",
            "xunit",
            "--output",
            "artifacts/dredd-xunit.xml",
        )

        results["dredd"] = _run(
            dredd_cmd,
            "dredd.log",
        )

    except FileNotFoundError as exc:

        results["dredd"] = {
            "command": ["npx", "dredd"],
            "return_code": None,
            "passed": False,
            "available": False,
            "stdout": "",
            "stderr": str(exc),
            "log": None,
        }

    except Exception as exc:

        results["dredd"] = {
            "command": ["npx", "dredd"],
            "return_code": None,
            "passed": False,
            "available": False,
            "stdout": "",
            "stderr": (
                "Failed to prepare Dredd specification: "
                f"{exc}"
            ),
            "log": None,
        }

    # =========================================================
    # 4. NEWMAN
    # =========================================================

    try:

        generated_collection = (
                ROOT
                / "postman"
                / "generated_collection.json"
        )

        if not generated_collection.exists():

            results["newman"] = {
                "command": [],
                "return_code": None,
                "passed": False,
                "available": False,
                "stdout": "",
                "stderr": (
                    "AI-generated Postman collection was not found: "
                    f"{generated_collection}"
                ),
                "log": None,
            }

        else:

            newman_cmd = _npx_command(
                "newman",
                "run",
                str(generated_collection),
                "--reporters",
                "cli,json",
                "--reporter-json-export",
                "artifacts/newman.json",
            )

            results["newman"] = _run(
                newman_cmd,
                "newman.log",
            )

    except FileNotFoundError as exc:

        results["newman"] = {
            "command": ["npx", "newman"],
            "return_code": None,
            "passed": False,
            "available": False,
            "stdout": "",
            "stderr": str(exc),
            "log": None,
        }
    # =========================================================
    # 5. PLAYWRIGHT
    # =========================================================

    try:

        playwright_cmd = _npx_command(
            "playwright",
            "test",
        )

        results["playwright"] = _run(
            playwright_cmd,
            "playwright.log",
        )

    except FileNotFoundError as exc:

        results["playwright"] = {
            "command": [
                "npx",
                "playwright",
                "test",
            ],
            "return_code": None,
            "passed": False,
            "available": False,
            "stdout": "",
            "stderr": str(exc),
            "log": None,
        }
    # =========================================================
    # UNIFIED RESULTS
    # =========================================================

    summary = {
        "total_tools": len(results),

        "available_tools": sum(
            1
            for result in results.values()
            if result.get("available")
        ),

        "passed_tools": sum(
            1
            for result in results.values()
            if result.get("passed")
        ),

        "failed_tools": sum(
            1
            for result in results.values()
            if result.get("available")
            and not result.get("passed")
        ),
    }

    payload = {
        "summary": summary,
        "results": results,
    }

    (ARTIFACTS / "contract-results.json").write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    return results