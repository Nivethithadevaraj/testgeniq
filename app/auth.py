from typing import Optional

users_db = {}

def register_user(username: str, password: str) -> dict:
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if username in users_db:
        raise ValueError("Username already exists")
    users_db[username] = {"username": username, "password": password, "active": True}
    return {"username": username, "message": "User registered successfully"}

def login_user(username: str, password: str) -> dict:
    if username not in users_db:
        raise ValueError("User not found")
    if users_db[username]["password"] != password:
        raise ValueError("Invalid password")
    if not users_db[username]["active"]:
        raise ValueError("Account is deactivated")
    return {"username": username, "token": f"token_{username}_abc123", "message": "Login successful"}

def get_user(username: str) -> Optional[dict]:
    return users_db.get(username)

def deactivate_user(username: str) -> bool:
    if username not in users_db:
        return False
    users_db[username]["active"] = False
    return True

def clear_users():
    global users_db
    users_db = {}
