import pytest
from app.auth import register_user, login_user, get_user, deactivate_user

def test_register_positive():
    r=register_user("testuser","password123")
    assert r["username"]=="testuser"

def test_register_empty_username():
    with pytest.raises(ValueError): register_user("","password123")

def test_register_short_password():
    with pytest.raises(ValueError): register_user("u","123")

def test_register_duplicate():
    register_user("u","password123")
    with pytest.raises(ValueError): register_user("u","password123")

def test_login_positive():
    register_user("u","password123")
    assert login_user("u","password123")["username"]=="u"

def test_login_unknown():
    with pytest.raises(ValueError): login_user("missing","password123")

def test_login_wrong_password():
    register_user("u","password123")
    with pytest.raises(ValueError): login_user("u","wrong123")

def test_get_user():
    register_user("u","password123")
    assert get_user("u")["active"] is True

def test_get_missing_user():
    assert get_user("missing") is None

def test_deactivate():
    register_user("u","password123")
    assert deactivate_user("u") is True
    with pytest.raises(ValueError): login_user("u","password123")

def test_deactivate_missing():
    assert deactivate_user("missing") is False
