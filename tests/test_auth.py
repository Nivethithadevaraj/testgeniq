import pytest

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
