import pytest
from app.tasks import create_task, get_all_tasks, get_task_by_id, update_task, delete_task

def test_create_task_positive():
    t=create_task("A","D","high")
    assert t["id"]==1 and t["title"]=="A" and t["priority"]=="high"

def test_create_task_negative_empty():
    with pytest.raises(ValueError): create_task("","D","medium")

def test_create_task_edge_invalid_priority():
    with pytest.raises(ValueError): create_task("A","D","urgent")

def test_get_all_tasks_positive():
    create_task("A")
    assert len(get_all_tasks())==1

def test_get_task_existing():
    create_task("A")
    assert get_task_by_id(1)["title"]=="A"

def test_get_task_missing():
    assert get_task_by_id(999) is None

def test_update_title():
    create_task("A")
    assert update_task(1,title="B")["title"]=="B"

def test_update_completed():
    create_task("A")
    assert update_task(1,completed=True)["completed"] is True

def test_update_missing():
    assert update_task(999,title="B") is None

def test_update_blank_title():
    create_task("A")
    with pytest.raises(ValueError): update_task(1,title=" ")

def test_delete_existing():
    create_task("A")
    assert delete_task(1) is True

def test_delete_missing():
    assert delete_task(999) is False
