import pytest
from app import tasks

# Fixtures --------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_state():
    """Ensure a clean task database before each test."""
    tasks.clear_tasks()
    yield
    tasks.clear_tasks()


# Helper ---------------------------------------------------------------

def create_sample_task(title="Sample Task", description="Desc", priority="medium"):
    """Create a task using the public API and return the dict."""
    return tasks.create_task(title=title, description=description, priority=priority)


# Tests for create_task --------------------------------------------------

def test_create_task_positive():
    """POSITIVE SCENARIO: create a task with all valid arguments."""
    task = tasks.create_task(title="Buy Groceries", description="Milk, Eggs", priority="high")
    assert isinstance(task, dict)
    assert task["id"] == 1
    assert task["title"] == "Buy Groceries"
    assert task["description"] == "Milk, Eggs"
    assert task["priority"] == "high"
    assert task["completed"] is False

def test_create_task_title_whitespace_edge():
    """EDGE CASE: title with surrounding whitespace should be stripped."""
    task = tasks.create_task(title="  padded title  ")
    assert task["title"] == "padded title"

def test_create_task_invalid_title_negative():
    """NEGATIVE SCENARIO: empty or whitespace‑only title raises ValueError."""
    with pytest.raises(ValueError, match="Title cannot be empty"):
        tasks.create_task(title="")
    with pytest.raises(ValueError, match="Title cannot be empty"):
        tasks.create_task(title="   ")

def test_create_task_invalid_priority_negative():
    """NEGATIVE SCENARIO: priority not in allowed set raises ValueError."""
    with pytest.raises(ValueError, match="Priority must be low, medium, or high"):
        tasks.create_task(title="Task", priority="urgent")
    with pytest.raises(ValueError, match="Priority must be low, medium, or high"):
        tasks.create_task(title="Task", priority="LOW")


# Tests for get_all_tasks -----------------------------------------------

def test_get_all_tasks_positive():
    """POSITIVE SCENARIO: retrieve all tasks after creating several."""
    t1 = create_sample_task(title="T1")
    t2 = create_sample_task(title="T2", priority="low")
    all_tasks = tasks.get_all_tasks()
    assert isinstance(all_tasks, list)
    assert len(all_tasks) == 2
    ids = {t["id"] for t in all_tasks}
    assert ids == {t1["id"], t2["id"]}

def test_get_all_tasks_empty_edge():
    """EDGE CASE: when no tasks exist, an empty list is returned."""
    assert tasks.get_all_tasks() == []


# Tests for get_task_by_id ----------------------------------------------

def test_get_task_by_id_positive():
    """POSITIVE SCENARIO: retrieve an existing task by its id."""
    task = create_sample_task(title="Find Me")
    fetched = tasks.get_task_by_id(task["id"])
    assert fetched == task

def test_get_task_by_id_nonexistent_edge():
    """EDGE CASE: requesting a non‑existent id returns None."""
    assert tasks.get_task_by_id(999) is None
    assert tasks.get_task_by_id(0) is None
    assert tasks.get_task_by_id(-1) is None


# Tests for update_task -------------------------------------------------

def test_update_task_positive():
    """POSITIVE SCENARIO: update title and completed flag."""
    task = create_sample_task(title="Old Title")
    updated = tasks.update_task(task_id=task["id"], title="New Title", completed=True)
    assert updated["id"] == task["id"]
    assert updated["title"] == "New Title"
    assert updated["completed"] is True
    # unchanged fields remain the same
    assert updated["description"] == task["description"]
    assert updated["priority"] == task["priority"]

def test_update_task_title_whitespace_edge():
    """EDGE CASE: title whitespace is stripped on update."""
    task = create_sample_task(title="Initial")
    updated = tasks.update_task(task_id=task["id"], title="  trimmed  ")
    assert updated["title"] == "trimmed"

def test_update_task_no_changes_edge():
    """EDGE CASE: passing None for both optional args leaves task unchanged."""
    task = create_sample_task(title="Static")
    unchanged = tasks.update_task(task_id=task["id"])
    assert unchanged == task

def test_update_task_invalid_title_negative():
    """NEGATIVE SCENARIO: empty title on update raises ValueError."""
    task = create_sample_task()
    with pytest.raises(ValueError, match="Title cannot be empty"):
        tasks.update_task(task_id=task["id"], title="   ")

def test_update_task_nonexistent_edge():
    """EDGE CASE: updating a non‑existent task returns None."""
    assert tasks.update_task(task_id=999, title="Nope") is None


# Tests for delete_task -------------------------------------------------

def test_delete_task_positive():
    """POSITIVE SCENARIO: delete an existing task."""
    task = create_sample_task()
    result = tasks.delete_task(task_id=task["id"])
    assert result is True
    # subsequent fetch should be None
    assert tasks.get_task_by_id(task["id"]) is None

def test_delete_task_twice_edge():
    """EDGE CASE: deleting the same task twice yields True then False."""
    task = create_sample_task()
    first = tasks.delete_task(task_id=task["id"])
    second = tasks.delete_task(task_id=task["id"])
    assert first is True
    assert second is False

def test_delete_task_nonexistent_edge():
    """EDGE CASE: deleting a non‑existent id returns False."""
    assert tasks.delete_task(task_id=12345) is False


# Tests for clear_tasks -------------------------------------------------

def test_clear_tasks_resets_state():
    """POSITIVE SCENARIO: clear_tasks empties DB and resets id counter."""
    t1 = create_sample_task()
    t2 = create_sample_task()
    assert len(tasks.get_all_tasks()) == 2
    tasks.clear_tasks()
    assert tasks.get_all_tasks() == []
    # New task after clear should start at id 1 again
    t3 = tasks.create_task(title="First After Clear")
    assert t3["id"] == 1
    # Ensure previous ids are not reused unintentionally
    assert t3["id"] != t1["id"] or t1["id"] == 1  # t1 may have been 1, but state is reset

def test_clear_tasks_multiple_calls_edge():
    """EDGE CASE: calling clear_tasks repeatedly does not raise."""
    tasks.clear_tasks()
    tasks.clear_tasks()  # should be a no‑op and not fail
    assert tasks.get_all_tasks() == []