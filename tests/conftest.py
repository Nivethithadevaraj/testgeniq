import pytest
from app.tasks import clear_tasks
from app.auth import clear_users

@pytest.fixture(autouse=True)
def reset_state():
    clear_tasks()
    clear_users()
    yield
    clear_tasks()
    clear_users()
