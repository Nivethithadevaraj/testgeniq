import pytest
from app import auth


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure a clean users_db before each test."""
    auth.clear_users()


# ==========================
# register_user tests
# ==========================
def test_register_user_positive():
    """POSITIVE SCENARIO: Register a user with valid credentials."""
    result = auth.register_user("alice", "password123")
    assert result == {"username": "alice", "message": "User registered successfully"}
    # Verify internal state
    user = auth.get_user("alice")
    assert user is not None
    assert user["username"] == "alice"
    assert user["password"] == "password123"
    assert user["active"] is True


def test_register_user_negative_empty_username():
    """NEGATIVE SCENARIO: Empty username should raise ValueError."""
    with pytest.raises(ValueError) as exc:
        auth.register_user("", "validPass")
    assert str(exc.value) == "Username cannot be empty"


def test_register_user_negative_whitespace_username():
    """NEGATIVE SCENARIO: Whitespace-only username should raise ValueError."""
    with pytest.raises(ValueError) as exc:
        auth.register_user("   ", "validPass")
    assert str(exc.value) == "Username cannot be empty"


def test_register_user_negative_short_password():
    """NEGATIVE SCENARIO: Password shorter than 6 characters should raise ValueError."""
    with pytest.raises(ValueError) as exc:
        auth.register_user("bob", "12345")
    assert str(exc.value) == "Password must be at least 6 characters"


def test_register_user_negative_duplicate_username():
    """NEGATIVE SCENARIO: Registering an existing username should raise ValueError."""
    auth.register_user("charlie", "securePass")
    with pytest.raises(ValueError) as exc:
        auth.register_user("charlie", "anotherPass")
    assert str(exc.value) == "Username already exists"


def test_register_user_edge_password_length():
    """EDGE CASE: Password exactly 6 characters should be accepted."""
    result = auth.register_user("dave", "123456")
    assert result == {"username": "dave", "message": "User registered successfully"}
    user = auth.get_user("dave")
    assert user is not None
    assert user["password"] == "123456"


# ==========================
# login_user tests
# ==========================
def test_login_user_positive():
    """POSITIVE SCENARIO: Successful login returns correct token and message."""
    auth.register_user("eve", "strongPass")
    result = auth.login_user("eve", "strongPass")
    expected_token = f"token_eve_abc123"
    assert result == {
        "username": "eve",
        "token": expected_token,
        "message": "Login successful",
    }


def test_login_user_negative_user_not_found():
    """NEGATIVE SCENARIO: Logging in with a non‑existent user raises ValueError."""
    with pytest.raises(ValueError) as exc:
        auth.login_user("nonexistent", "anyPass")
    assert str(exc.value) == "User not found"


def test_login_user_negative_invalid_password():
    """NEGATIVE SCENARIO: Incorrect password raises ValueError."""
    auth.register_user("frank", "correctPass")
    with pytest.raises(ValueError) as exc:
        auth.login_user("frank", "wrongPass")
    assert str(exc.value) == "Invalid password"


def test_login_user_negative_deactivated_account():
    """NEGATIVE SCENARIO: Deactivated account cannot log in."""
    auth.register_user("grace", "pass123")
    auth.deactivate_user("grace")
    with pytest.raises(ValueError) as exc:
        auth.login_user("grace", "pass123")
    assert str(exc.value) == "Account is deactivated"


def test_login_user_edge_deactivated_then_login():
    """EDGE CASE: Attempt login immediately after deactivation should fail."""
    auth.register_user("heidi", "pwd12345")
    # Deactivate first
    auth.deactivate_user("heidi")
    # Then attempt login
    with pytest.raises(ValueError) as exc:
        auth.login_user("heidi", "pwd12345")
    assert str(exc.value) == "Account is deactivated"


# ==========================
# get_user tests
# ==========================
def test_get_user_positive():
    """POSITIVE SCENARIO: Retrieve an existing user's internal dict."""
    auth.register_user("ivan", "secretPass")
    user = auth.get_user("ivan")
    assert isinstance(user, dict)
    assert user["username"] == "ivan"
    assert user["password"] == "secretPass"
    assert user["active"] is True


def test_get_user_negative_not_found():
    """NEGATIVE SCENARIO: Querying a non‑existent user returns None."""
    assert auth.get_user("nonexistent") is None


def test_get_user_edge_deactivated():
    """EDGE CASE: Retrieve a deactivated user; active flag should be False."""
    auth.register_user("judy", "pwd123")
    auth.deactivate_user("judy")
    user = auth.get_user("judy")
    assert user is not None
    assert user["active"] is False


# ==========================
# deactivate_user tests
# ==========================
def test_deactivate_user_positive():
    """POSITIVE SCENARIO: Deactivate an existing user returns True."""
    auth.register_user("ken", "pass123")
    result = auth.deactivate_user("ken")
    assert result is True
    user = auth.get_user("ken")
    assert user["active"] is False


def test_deactivate_user_negative_not_found():
    """NEGATIVE SCENARIO: Deactivating a non‑existent user returns False."""
    result = auth.deactivate_user("ghost")
    assert result is False


def test_deactivate_user_edge_multiple_calls():
    """EDGE CASE: Deactivating the same user twice still returns True."""
    auth.register_user("laura", "pwd456")
    first = auth.deactivate_user("laura")
    second = auth.deactivate_user("laura")
    assert first is True
    assert second is True
    user = auth.get_user("laura")
    assert user["active"] is False


# ==========================
# clear_users tests
# ==========================
def test_clear_users_positive():
    """POSITIVE SCENARIO: clear_users resets the in‑memory database."""
    auth.register_user("mike", "pass789")
    auth.register_user("nina", "pass321")
    # Ensure users exist before clearing
    assert auth.get_user("mike") is not None
    assert auth.get_user("nina") is not None
    # Clear all users
    auth.clear_users()
    assert auth.get_user("mike") is None
    assert auth.get_user("nina") is None
    # Also verify that the internal dict is empty (indirectly via get_user)
    # No further state to check; absence of users confirms the reset.