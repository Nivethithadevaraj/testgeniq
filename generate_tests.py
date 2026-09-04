from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from dotenv import load_dotenv

from engine.ai import generate_test_code


ROOT = Path(__file__).resolve().parent
TESTS_DIR = ROOT / "tests"
OPENAPI_FILE = ROOT / "openapi.json"
ARTIFACTS_DIR = ROOT / "artifacts"

TESTS_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)


# ============================================================
# SOURCE DISCOVERY
# ============================================================

def discover_source_modules() -> list[Path]:
    """
    TestGenIQ target application modules.
    """

    modules = [
        ROOT / "app" / "tasks.py",
        ROOT / "app" / "auth.py",
    ]

    return [
        path
        for path in modules
        if path.exists()
    ]


def extract_public_functions(
    source_file: Path,
) -> list[str]:
    """
    Extract actual public functions from the source module.
    """

    tree = ast.parse(
        source_file.read_text(
            encoding="utf-8"
        )
    )

    functions = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if not node.name.startswith("_"):
                functions.append(node.name)

    return functions


def extract_function_signatures(
    source_file: Path,
) -> str:
    """
    Extract actual function definitions to give the AI
    an explicit source-of-truth signature reference.
    """

    source = source_file.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    signatures = []

    for node in tree.body:

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name.startswith("_"):
            continue

        try:
            signature = ast.unparse(node.args)
        except Exception:
            signature = "signature unavailable"

        signatures.append(
            f"{node.name}({signature})"
        )

    return "\n".join(signatures)


# ============================================================
# OPENAPI
# ============================================================

def load_openapi() -> dict:
    if not OPENAPI_FILE.exists():
        return {}

    return json.loads(
        OPENAPI_FILE.read_text(
            encoding="utf-8-sig"
        )
    )


def build_generation_context(
    source_file: Path,
    openapi: dict,
) -> str:

    source = source_file.read_text(
        encoding="utf-8"
    )

    relevant_routes = []

    for path, path_item in openapi.get(
        "paths",
        {},
    ).items():

        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():

            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }:
                continue

            if not isinstance(
                operation,
                dict,
            ):
                continue

            relevant_routes.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operationId": operation.get(
                        "operationId"
                    ),
                    "summary": operation.get(
                        "summary"
                    ),
                    "requestBody": operation.get(
                        "requestBody"
                    ),
                    "responses": operation.get(
                        "responses",
                        {},
                    ),
                }
            )

    functions = extract_public_functions(
        source_file
    )

    signatures = extract_function_signatures(
        source_file
    )

    return f"""
TARGET SOURCE FILE
==================
{source_file}

ACTUAL PUBLIC FUNCTIONS
=======================
{functions}

ACTUAL FUNCTION SIGNATURES
==========================
{signatures}

SOURCE CODE
===========
{source}

OPENAPI CONTRACT
================
{json.dumps(relevant_routes, indent=2)}
"""


# ============================================================
# CODE CLEANING
# ============================================================

def sanitize_generated_code(
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
# SOURCE-AWARE VALIDATION
# ============================================================

def validate_generated_test_code(
    code: str,
    source_file: Path,
) -> tuple[bool, list[str]]:
    """
    Validate AI output against the REAL source module.

    This prevents generated tests from importing nonexistent
    functions such as get_task.
    """

    problems = []

    if not code.strip():
        return False, ["Generated code is empty."]

    if "import pytest" not in code:
        problems.append(
            "Missing pytest import."
        )

    if "def test_" not in code:
        problems.append(
            "No pytest test functions found."
        )

    try:
        tree = ast.parse(code)

    except SyntaxError as exc:
        problems.append(
            f"Syntax error: {exc}"
        )
        return False, problems

    actual_functions = set(
        extract_public_functions(
            source_file
        )
    )

    imported_functions = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module == (
                f"app.{source_file.stem}"
            ):

                for alias in node.names:

                    if alias.name != "*":
                        imported_functions.add(
                            alias.name
                        )

    invalid_imports = (
        imported_functions
        - actual_functions
    )

    if invalid_imports:

        problems.append(
            "Generated tests import nonexistent "
            f"functions: {sorted(invalid_imports)}"
        )

    # --------------------------------------------------------
    # Scenario markers
    # --------------------------------------------------------

    normalized_code = code.upper()

    if "POSITIVE" not in normalized_code:
        problems.append(
            "Missing POSITIVE scenario."
        )

    if "NEGATIVE" not in normalized_code:
        problems.append(
            "Missing NEGATIVE scenario."
        )

    if "EDGE" not in normalized_code:
        problems.append(
            "Missing EDGE scenario."
        )

    return (
        len(problems) == 0,
        problems,
    )


# ============================================================
# FALLBACK TESTS
# ============================================================

def fallback_tests(
    module_name: str,
) -> str:

    if module_name == "tasks":

        return '''import pytest

from app.tasks import (
    clear_tasks,
    create_task,
    get_all_tasks,
    get_task_by_id,
    update_task,
    delete_task,
)


@pytest.fixture(autouse=True)
def reset_tasks():
    clear_tasks()
    yield
    clear_tasks()


# POSITIVE SCENARIO
def test_create_task_positive():
    task = create_task(
        title="Prepare report",
        description="Prepare the weekly report",
        priority="high",
    )

    assert task["title"] == "Prepare report"
    assert task["description"] == "Prepare the weekly report"
    assert task["priority"] == "high"
    assert task["completed"] is False


# NEGATIVE SCENARIO
def test_create_task_negative_invalid_priority():
    with pytest.raises(
        ValueError,
        match="Priority must be low, medium, or high",
    ):
        create_task(
            title="Invalid task",
            priority="invalid",
        )


# EDGE CASE
def test_create_task_edge_empty_title():
    with pytest.raises(
        ValueError,
        match="Title cannot be empty",
    ):
        create_task(
            title="",
            priority="low",
        )


# POSITIVE SCENARIO
def test_get_all_tasks_positive():
    create_task(
        title="Task one",
        priority="low",
    )

    create_task(
        title="Task two",
        priority="high",
    )

    result = get_all_tasks()

    assert len(result) == 2
    assert result[0]["title"] == "Task one"
    assert result[1]["title"] == "Task two"


# NEGATIVE SCENARIO
def test_get_all_tasks_negative_empty_store():
    result = get_all_tasks()

    assert result == []


# EDGE CASE
def test_get_all_tasks_edge_after_delete():
    task = create_task(
        title="Temporary task",
        priority="medium",
    )

    delete_task(task["id"])

    assert get_all_tasks() == []


# POSITIVE SCENARIO
def test_get_task_by_id_positive():
    task = create_task(
        title="Read specification",
        priority="medium",
    )

    result = get_task_by_id(task["id"])

    assert result is not None
    assert result["id"] == task["id"]


# NEGATIVE SCENARIO
def test_get_task_by_id_negative_missing_id():
    assert get_task_by_id(999999) is None


# EDGE CASE
def test_get_task_by_id_edge_first_id():
    task = create_task(
        title="First task",
        priority="low",
    )

    assert get_task_by_id(1) == task


# POSITIVE SCENARIO
def test_update_task_positive():
    task = create_task(
        title="Original",
        priority="low",
    )

    result = update_task(
        task["id"],
        title="Updated",
        completed=True,
    )

    assert result is not None
    assert result["title"] == "Updated"
    assert result["completed"] is True


# NEGATIVE SCENARIO
def test_update_task_negative_missing_task():
    result = update_task(
        999999,
        title="Missing",
    )

    assert result is None


# EDGE CASE
def test_update_task_edge_blank_title():
    task = create_task(
        title="Original",
        priority="low",
    )

    with pytest.raises(
        ValueError,
        match="Title cannot be empty",
    ):
        update_task(
            task["id"],
            title="",
        )


# POSITIVE SCENARIO
def test_delete_task_positive():
    task = create_task(
        title="Delete me",
        priority="low",
    )

    assert delete_task(task["id"]) is True
    assert get_task_by_id(task["id"]) is None


# NEGATIVE SCENARIO
def test_delete_task_negative_missing_task():
    assert delete_task(999999) is False


# EDGE CASE
def test_delete_task_edge_repeated_delete():
    task = create_task(
        title="Delete twice",
        priority="low",
    )

    assert delete_task(task["id"]) is True
    assert delete_task(task["id"]) is False
'''


    if module_name == "auth":

        return '''import pytest

from app.auth import (
    clear_users,
    register_user,
    login_user,
    get_user,
    deactivate_user,
)


@pytest.fixture(autouse=True)
def reset_users():
    clear_users()
    yield
    clear_users()


# POSITIVE SCENARIO
def test_register_user_positive():
    result = register_user(
        "testuser",
        "password123",
    )

    assert result["username"] == "testuser"
    assert result["message"] == "User registered successfully"

    stored = get_user("testuser")

    assert stored is not None
    assert stored["active"] is True


# NEGATIVE SCENARIO
def test_register_user_negative_duplicate():
    register_user(
        "testuser",
        "password123",
    )

    with pytest.raises(
        ValueError,
        match="Username already exists",
    ):
        register_user(
            "testuser",
            "password123",
        )


# EDGE CASE
def test_register_user_edge_short_password():
    with pytest.raises(
        ValueError,
        match="Password must be at least 6 characters",
    ):
        register_user(
            "shortpass",
            "12345",
        )


# POSITIVE SCENARIO
def test_login_user_positive():
    register_user(
        "testuser",
        "password123",
    )

    result = login_user(
        "testuser",
        "password123",
    )

    assert result["username"] == "testuser"
    assert result["token"].startswith("token_testuser_")
    assert result["message"] == "Login successful"


# NEGATIVE SCENARIO
def test_login_user_negative_wrong_password():
    register_user(
        "testuser",
        "password123",
    )

    with pytest.raises(
        ValueError,
        match="Invalid password",
    ):
        login_user(
            "testuser",
            "wrong-password",
        )


# EDGE CASE
def test_login_user_edge_unknown_user():
    with pytest.raises(
        ValueError,
        match="User not found",
    ):
        login_user(
            "unknown-user",
            "password123",
        )


# POSITIVE SCENARIO
def test_get_user_positive():
    register_user(
        "testuser",
        "password123",
    )

    user = get_user("testuser")

    assert user is not None
    assert user["username"] == "testuser"
    assert user["active"] is True


# NEGATIVE SCENARIO
def test_get_user_negative_missing_user():
    assert get_user("missing") is None


# EDGE CASE
def test_get_user_edge_empty_username():
    assert get_user("") is None


# POSITIVE SCENARIO
def test_deactivate_user_positive():
    register_user(
        "testuser",
        "password123",
    )

    result = deactivate_user(
        "testuser"
    )

    assert result is True

    user = get_user("testuser")

    assert user is not None
    assert user["active"] is False


# NEGATIVE SCENARIO
def test_deactivate_user_negative_missing_user():
    assert deactivate_user(
        "missing"
    ) is False


# EDGE CASE
def test_deactivate_user_edge_login_after_deactivation():
    register_user(
        "testuser",
        "password123",
    )

    deactivate_user(
        "testuser"
    )

    with pytest.raises(
        ValueError,
        match="Account is deactivated",
    ):
        login_user(
            "testuser",
            "password123",
        )
'''

    return ""


# ============================================================
# GENERATE ONE MODULE
# ============================================================

def generate_module_tests(
    source_file: Path,
    openapi: dict,
) -> tuple[str, bool]:

    module_name = source_file.stem

    context = build_generation_context(
        source_file,
        openapi,
    )

    prompt = f"""
You are TestGenIQ's automated pytest test-generation engine.

Generate executable pytest unit tests for:

MODULE:
{module_name}

SOURCE OF TRUTH
===============
The supplied Python source is authoritative.

You MUST use only functions that actually exist in:

app.{module_name}

ACTUAL FUNCTIONS:
{extract_public_functions(source_file)}

ACTUAL SIGNATURES:
{extract_function_signatures(source_file)}

MANDATORY SCENARIOS
===================

For every important business function:

1. POSITIVE SCENARIO
   Test valid normal behavior.

2. NEGATIVE SCENARIO
   Test invalid input, missing resources, invalid state,
   or explicitly raised errors.

3. EDGE CASE
   Test an empty/boundary/repeated/state-transition case
   that is actually supported by the source.

STRICT RULES
============

- Do NOT invent function names.
- Do NOT invent parameters.
- Do NOT invent return fields.
- Do NOT invent exceptions.
- Do NOT invent validation rules.
- Do NOT pass parameters that are not in the function signature.
- Do NOT assume return types that contradict the source.
- Import only actual functions.
- Use pytest.
- Reset in-memory state using the actual clear_* function.
- Every test must be executable.
- Include POSITIVE SCENARIO comments.
- Include NEGATIVE SCENARIO comments.
- Include EDGE CASE comments.
- Return Python source only.
- No Markdown fences.

SOURCE / OPENAPI CONTEXT
========================
{context}
"""

    try:

        generated = generate_test_code(
            prompt=prompt,
            module_name=module_name,
        )

        generated = sanitize_generated_code(
            generated
        )

        valid, problems = (
            validate_generated_test_code(
                generated,
                source_file,
            )
        )

        if valid:

            print(
                f"AI-generated tests validated for "
                f"{module_name}"
            )

            return generated, True

        print(
            f"AI output rejected for {module_name}:"
        )

        for problem in problems:
            print(f"  - {problem}")

    except Exception as exc:

        print(
            f"AI generation failed for "
            f"{module_name}: {exc}"
        )

    print(
        f"Using deterministic source-safe fallback "
        f"for {module_name}"
    )

    return (
        fallback_tests(module_name),
        False,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    load_dotenv()

    openapi = load_openapi()

    source_modules = (
        discover_source_modules()
    )

    generated_files = []
    generation_modes = {}

    for source_file in source_modules:

        module_name = source_file.stem

        print()
        print(
            f"Generating AI pytest suite: "
            f"{module_name}"
        )

        test_code, ai_generated = (
            generate_module_tests(
                source_file,
                openapi,
            )
        )

        target = (
            TESTS_DIR
            / f"test_{module_name}.py"
        )

        target.write_text(
            test_code,
            encoding="utf-8",
        )

        generated_files.append(
            str(
                target.relative_to(ROOT)
            )
        )

        generation_modes[
            module_name
        ] = (
            "AI"
            if ai_generated
            else "deterministic_fallback"
        )

        print(
            f"Generated: {target}"
        )

    manifest = {
        "generator": "TestGenIQ",
        "source_of_truth": (
            "OpenAPI + Python source"
        ),
        "generated_files": generated_files,
        "generation_modes": generation_modes,
        "scenario_types": [
            "positive",
            "negative",
            "edge",
        ],
        "source_modules": [
            str(
                path.relative_to(ROOT)
            )
            for path in source_modules
        ],
    }

    manifest_path = (
        ARTIFACTS_DIR
        / "generation-manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "AI TEST GENERATION COMPLETE"
    )

    print(
        json.dumps(
            manifest,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()