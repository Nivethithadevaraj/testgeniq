from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENAPI = ROOT / "openapi.json"
DEFAULT_OUTPUT = ROOT / "postman" / "generated_collection.json"


def _test_script(expected_status: int, extra: list[str] | None = None):
    lines = [
        f'pm.test("Status code is {expected_status}", function () {{',
        f"    pm.response.to.have.status({expected_status});",
        "});",
        "",
        'pm.test("Response is JSON", function () {',
        "    pm.response.json();",
        "});",
    ]

    if extra:
        lines.extend([""] + extra)

    return {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": lines,
        },
    }


def _prerequest_script(lines: list[str]):
    return {
        "listen": "prerequest",
        "script": {
            "type": "text/javascript",
            "exec": lines,
        },
    }


def _item(
    name: str,
    method: str,
    path: str,
    expected_status: int,
    body: dict | None = None,
    prerequest: list[str] | None = None,
    extra_tests: list[str] | None = None,
):
    request = {
        "method": method,
        "header": [],
        "url": f"{{{{baseUrl}}}}{path}",
    }

    if body is not None:
        request["header"] = [
            {
                "key": "Content-Type",
                "value": "application/json",
            }
        ]

        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body),
            "options": {
                "raw": {
                    "language": "json",
                }
            },
        }

    events = []

    if prerequest:
        events.append(
            _prerequest_script(prerequest)
        )

    events.append(
        _test_script(
            expected_status,
            extra_tests,
        )
    )

    return {
        "name": name,
        "event": events,
        "request": request,
    }


def build_collection(openapi: dict) -> dict:
    """
    Build the executable TestGenIQ Postman suite.

    The ordering is intentional because task/user endpoints use
    in-memory state.

    Scenario categories:
        POSITIVE
        NEGATIVE
        EDGE_CASE
    """

    title = (
        openapi.get("info", {})
        .get("title", "TestGenIQ Target API")
    )

    items = []

    # ========================================================
    # BASIC API
    # ========================================================

    items.append(
        _item(
            "GET /health [POSITIVE]",
            "GET",
            "/health",
            200,
        )
    )

    items.append(
        _item(
            "GET / [POSITIVE]",
            "GET",
            "/",
            200,
        )
    )

    # ========================================================
    # TASK FLOW
    # ========================================================

    items.append(
        _item(
            "POST /tasks [POSITIVE]",
            "POST",
            "/tasks",
            200,
            body={
                "title": "TestGenIQ Newman Task",
                "description": "Created by generated Postman collection",
                "priority": "high",
            },
            extra_tests=[
                "const body = pm.response.json();",
                'pm.collectionVariables.set("task_id", String(body.id));',
                "",
                'pm.test("Created task contains an id", function () {',
                "    pm.expect(body.id).to.exist;",
                "});",
            ],
        )
    )

    items.append(
        _item(
            "GET /tasks [POSITIVE]",
            "GET",
            "/tasks",
            200,
        )
    )

    items.append(
        _item(
            "GET /tasks/{task_id} [POSITIVE]",
            "GET",
            "/tasks/{{task_id}}",
            200,
        )
    )

    items.append(
        _item(
            "PUT /tasks/{task_id} [POSITIVE]",
            "PUT",
            "/tasks/{{task_id}}",
            200,
            body={
                "title": "Updated Newman Task",
                "completed": True,
            },
        )
    )

    items.append(
        _item(
            "POST /tasks invalid priority [NEGATIVE]",
            "POST",
            "/tasks",
            400,
            body={
                "title": "Invalid Priority",
                "description": "",
                "priority": "critical",
            },
        )
    )

    items.append(
        _item(
            "GET /tasks/999999 [NEGATIVE]",
            "GET",
            "/tasks/999999",
            404,
        )
    )

    items.append(
        _item(
            "PUT /tasks/999999 [NEGATIVE]",
            "PUT",
            "/tasks/999999",
            404,
            body={
                "title": "Missing Task",
                "completed": True,
            },
        )
    )

    # Actual edge case based on create_task implementation:
    # blank title is rejected by business validation.
    items.append(
        _item(
            "POST /tasks blank title [EDGE_CASE]",
            "POST",
            "/tasks",
            400,
            body={
                "title": "",
                "description": "",
                "priority": "low",
            },
        )
    )

    items.append(
        _item(
            "DELETE /tasks/{task_id} [POSITIVE]",
            "DELETE",
            "/tasks/{{task_id}}",
            200,
        )
    )

    # Repeating deletion is an edge case.
    items.append(
        _item(
            "DELETE same task twice [EDGE_CASE]",
            "DELETE",
            "/tasks/{{task_id}}",
            404,
        )
    )

    # ========================================================
    # AUTH FLOW
    # ========================================================

    # Generate a fresh username on every Newman execution,
    # preventing duplicate-user failures across repeated runs.
    register_setup = [
        'pm.collectionVariables.set("username", "testgeniq_" + Date.now());',
        'pm.collectionVariables.set("password", "password123");',
    ]

    items.append(
        _item(
            "POST /auth/register [POSITIVE]",
            "POST",
            "/auth/register",
            200,
            body={
                "username": "{{username}}",
                "password": "{{password}}",
            },
            prerequest=register_setup,
        )
    )

    items.append(
        _item(
            "POST /auth/login [POSITIVE]",
            "POST",
            "/auth/login",
            200,
            body={
                "username": "{{username}}",
                "password": "{{password}}",
            },
        )
    )

    items.append(
        _item(
            "GET /users/{username} [POSITIVE]",
            "GET",
            "/users/{{username}}",
            200,
        )
    )

    # Wrong password is checked before active-state validation.
    items.append(
        _item(
            "POST /auth/login wrong password [NEGATIVE]",
            "POST",
            "/auth/login",
            400,
            body={
                "username": "{{username}}",
                "password": "wrong-password",
            },
        )
    )

    items.append(
        _item(
            "GET missing user [NEGATIVE]",
            "GET",
            "/users/no_such_user_zzz",
            404,
        )
    )

    items.append(
        _item(
            "POST deactivate missing user [NEGATIVE]",
            "POST",
            "/users/no_such_user_zzz/deactivate",
            404,
        )
    )

    # Password length < 6 is a real boundary from auth.py.
    items.append(
        _item(
            "POST /auth/register short password [EDGE_CASE]",
            "POST",
            "/auth/register",
            400,
            body={
                "username": "edge_user",
                "password": "12345",
            },
        )
    )

    items.append(
        _item(
            "POST /users/{username}/deactivate [POSITIVE]",
            "POST",
            "/users/{{username}}/deactivate",
            200,
        )
    )

    # Login after deactivation is a state-transition edge case.
    items.append(
        _item(
            "POST login after deactivation [EDGE_CASE]",
            "POST",
            "/auth/login",
            400,
            body={
                "username": "{{username}}",
                "password": "{{password}}",
            },
        )
    )

    return {
        "info": {
            "_postman_id": "testgeniq-generated-collection",
            "name": "TestGenIQ Generated Collection",
            "description": (
                "Generated by TestGenIQ from the OpenAPI/source-of-truth "
                "pipeline. Contains positive, negative and edge-case "
                "API validation scenarios."
            ),
            "schema": (
                "https://schema.getpostman.com/json/collection/"
                "v2.1.0/collection.json"
            ),
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://127.0.0.1:8000",
            },
            {
                "key": "task_id",
                "value": "",
            },
            {
                "key": "username",
                "value": "",
            },
            {
                "key": "password",
                "value": "password123",
            },
            {
                "key": "openapi_title",
                "value": title,
            },
        ],
        "item": items,
    }


def generate_postman_collection(
    openapi_path: str | Path = DEFAULT_OPENAPI,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> Path:
    """
    Generate postman/generated_collection.json.
    """

    openapi_path = Path(openapi_path)
    output_path = Path(output_path)

    if not openapi_path.exists():
        raise FileNotFoundError(
            f"OpenAPI specification not found: {openapi_path}"
        )

    openapi = json.loads(
        openapi_path.read_text(
            encoding="utf-8-sig"
        )
    )

    collection = build_collection(
        openapi
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            collection,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_path


# Backward-compatible names so existing pipeline code does not
# break if it imports an older function name.
def generate_collection(*args, **kwargs):
    return generate_postman_collection(
        *args,
        **kwargs,
    )


def generate_api_collection(*args, **kwargs):
    return generate_postman_collection(
        *args,
        **kwargs,
    )


if __name__ == "__main__":
    path = generate_postman_collection()
    print(f"Generated: {path}")