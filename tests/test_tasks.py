import pytest

from app.tasks import (
    clear_tasks,
    create_task,
    get_all_tasks,
    get_task_by_id,
    update_task,
    delete_task,
)


@pytest.fixture(autouse=True)
def reset_tasks():
    clear_tasks()
    yield
    clear_tasks()


# POSITIVE SCENARIO
def test_create_task_positive():
    task = create_task(
        title="Prepare report",
        description="Prepare the weekly report",
        priority="high",
    )

    assert task["title"] == "Prepare report"
    assert task["description"] == "Prepare the weekly report"
    assert task["priority"] == "high"
    assert task["completed"] is False


# NEGATIVE SCENARIO
def test_create_task_negative_invalid_priority():
    with pytest.raises(
        ValueError,
        match="Priority must be low, medium, or high",
    ):
        create_task(
            title="Invalid task",
            priority="invalid",
        )


# EDGE CASE
def test_create_task_edge_empty_title():
    with pytest.raises(
        ValueError,
        match="Title cannot be empty",
    ):
        create_task(
            title="",
            priority="low",
        )


# POSITIVE SCENARIO
def test_get_all_tasks_positive():
    create_task(
        title="Task one",
        priority="low",
    )

    create_task(
        title="Task two",
        priority="high",
    )

    result = get_all_tasks()

    assert len(result) == 2
    assert result[0]["title"] == "Task one"
    assert result[1]["title"] == "Task two"


# NEGATIVE SCENARIO
def test_get_all_tasks_negative_empty_store():
    result = get_all_tasks()

    assert result == []


# EDGE CASE
def test_get_all_tasks_edge_after_delete():
    task = create_task(
        title="Temporary task",
        priority="medium",
    )

    delete_task(task["id"])

    assert get_all_tasks() == []


# POSITIVE SCENARIO
def test_get_task_by_id_positive():
    task = create_task(
        title="Read specification",
        priority="medium",
    )

    result = get_task_by_id(task["id"])

    assert result is not None
    assert result["id"] == task["id"]


# NEGATIVE SCENARIO
def test_get_task_by_id_negative_missing_id():
    assert get_task_by_id(999999) is None


# EDGE CASE
def test_get_task_by_id_edge_first_id():
    task = create_task(
        title="First task",
        priority="low",
    )

    assert get_task_by_id(1) == task


# POSITIVE SCENARIO
def test_update_task_positive():
    task = create_task(
        title="Original",
        priority="low",
    )

    result = update_task(
        task["id"],
        title="Updated",
        completed=True,
    )

    assert result is not None
    assert result["title"] == "Updated"
    assert result["completed"] is True


# NEGATIVE SCENARIO
def test_update_task_negative_missing_task():
    result = update_task(
        999999,
        title="Missing",
    )

    assert result is None


# EDGE CASE
def test_update_task_edge_blank_title():
    task = create_task(
        title="Original",
        priority="low",
    )

    with pytest.raises(
        ValueError,
        match="Title cannot be empty",
    ):
        update_task(
            task["id"],
            title="",
        )


# POSITIVE SCENARIO
def test_delete_task_positive():
    task = create_task(
        title="Delete me",
        priority="low",
    )

    assert delete_task(task["id"]) is True
    assert get_task_by_id(task["id"]) is None


# NEGATIVE SCENARIO
def test_delete_task_negative_missing_task():
    assert delete_task(999999) is False


# EDGE CASE
def test_delete_task_edge_repeated_delete():
    task = create_task(
        title="Delete twice",
        priority="low",
    )

    assert delete_task(task["id"]) is True
    assert delete_task(task["id"]) is False
