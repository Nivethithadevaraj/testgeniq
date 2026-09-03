from fastapi.testclient import TestClient
from app.main import app
from app.tasks import clear_tasks
from app.auth import clear_users

client=TestClient(app)

def setup_function():
    clear_tasks(); clear_users()

def test_health(): assert client.get("/health").status_code==200

def test_create_task(): assert client.post("/tasks",json={"title":"A"}).status_code==200

def test_create_task_bad_priority(): assert client.post("/tasks",json={"title":"A","priority":"x"}).status_code==400

def test_get_tasks(): assert client.get("/tasks").status_code==200

def test_get_missing_task(): assert client.get("/tasks/999").status_code==404

def test_update_missing_task(): assert client.put("/tasks/999",json={"title":"A"}).status_code==404

def test_delete_missing_task(): assert client.delete("/tasks/999").status_code==404

def test_register(): assert client.post("/auth/register",json={"username":"u","password":"password123"}).status_code==200

def test_register_bad_password(): assert client.post("/auth/register",json={"username":"u","password":"123"}).status_code==400

def test_login_missing_user(): assert client.post("/auth/login",json={"username":"u","password":"password123"}).status_code==400

def test_get_missing_user(): assert client.get("/users/missing").status_code==404

def test_deactivate_missing_user(): assert client.post("/users/missing/deactivate").status_code==404
