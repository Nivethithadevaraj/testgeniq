"""
Tests for the safety checks applied to AI-generated tests
before they are accepted (post-submission).
"""

from pathlib import Path

import pytest

import generate_tests as gen


AUTH_SOURCE = gen.ROOT / "app" / "auth.py"


GOOD_AUTH_TESTS = '''
import pytest
from app.auth import register_user, clear_users


def test_register_positive():
    # POSITIVE SCENARIO
    clear_users()
    assert register_user("alice", "password123")["username"] == "alice"


def test_register_negative_short_password():
    # NEGATIVE SCENARIO
    clear_users()
    with pytest.raises(ValueError):
        register_user("bob", "123")


def test_register_edge_six_characters():
    # EDGE CASE
    clear_users()
    assert register_user("carol", "123456")["username"] == "carol"
'''


# The exact mistake seen on 10 Nov: a bare module import.
BARE_IMPORT_TESTS = GOOD_AUTH_TESTS.replace(
    "from app.auth import", "from auth import"
)


# Imports are fine, but one assertion expects the wrong behaviour.
WRONG_ASSERTION_TESTS = GOOD_AUTH_TESTS.replace(
    'register_user("carol", "123456")["username"] == "carol"',
    'register_user("carol", "123456")["username"] == "WRONG"',
)


# ------------------------------------------------------------
# Static check
# ------------------------------------------------------------

def test_static_check_accepts_good_tests():
    valid, problems = gen.validate_generated_test_code(
        GOOD_AUTH_TESTS, AUTH_SOURCE
    )
    assert valid, problems


def test_static_check_rejects_bare_module_import():
    valid, problems = gen.validate_generated_test_code(
        BARE_IMPORT_TESTS, AUTH_SOURCE
    )
    assert not valid
    assert any("app. package prefix" in p for p in problems)


def test_static_check_rejects_plain_import_statement():
    code = GOOD_AUTH_TESTS.replace(
        "from app.auth import register_user, clear_users",
        "import auth\nfrom app.auth import register_user, clear_users",
    )
    valid, problems = gen.validate_generated_test_code(code, AUTH_SOURCE)
    assert not valid
    assert any("auth" in p for p in problems)


# ------------------------------------------------------------
# Execution check
# ------------------------------------------------------------

def test_execution_check_passes_good_tests():
    passed, summary = gen.run_generated_tests(GOOD_AUTH_TESTS, "auth")
    assert passed, summary
    assert "3 passed" in summary


def test_execution_check_catches_wrong_assertion():
    passed, summary = gen.run_generated_tests(WRONG_ASSERTION_TESTS, "auth")
    assert not passed
    assert "failed" in summary


def test_execution_check_catches_bare_import():
    passed, _ = gen.run_generated_tests(BARE_IMPORT_TESTS, "auth")
    assert not passed


def test_execution_check_removes_candidate_file():
    gen.run_generated_tests(GOOD_AUTH_TESTS, "auth")
    assert not (gen.TESTS_DIR / "_candidate_auth.py").exists()


# ------------------------------------------------------------
# Retry and fallback
# ------------------------------------------------------------

def _fake_generator(outputs):
    calls = {"count": 0}

    def fake(prompt, module_name="api"):
        output = outputs[min(calls["count"], len(outputs) - 1)]
        calls["count"] += 1
        return output

    return fake, calls


def test_bad_first_attempt_is_retried(monkeypatch):
    fake, calls = _fake_generator([BARE_IMPORT_TESTS, GOOD_AUTH_TESTS])
    monkeypatch.setattr(gen, "generate_test_code", fake)

    code, ai_generated = gen.generate_module_tests(AUTH_SOURCE, {})

    assert ai_generated
    assert calls["count"] == 2
    assert "from app.auth import" in code


def test_failing_ai_tests_fall_back(monkeypatch):
    fake, calls = _fake_generator([WRONG_ASSERTION_TESTS])
    monkeypatch.setattr(gen, "generate_test_code", fake)

    code, ai_generated = gen.generate_module_tests(AUTH_SOURCE, {})

    assert not ai_generated
    assert calls["count"] == gen.MAX_GENERATION_ATTEMPTS
    assert code == gen.fallback_tests("auth")
