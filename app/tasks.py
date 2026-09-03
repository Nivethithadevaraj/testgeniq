tasks_db = {}
_next_task_id = 1

def create_task(title: str, description: str = "", priority: str = "medium") -> dict:
    global _next_task_id
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")
    if priority not in {"low", "medium", "high"}:
        raise ValueError("Priority must be low, medium, or high")
    task = {
        "id": _next_task_id,
        "title": title.strip(),
        "description": description,
        "priority": priority,
        "completed": False,
    }
    tasks_db[_next_task_id] = task
    _next_task_id += 1
    return task

def get_all_tasks() -> list[dict]:
    return list(tasks_db.values())

def get_task_by_id(task_id: int) -> dict | None:
    return tasks_db.get(task_id)

def update_task(task_id: int, title: str | None = None, completed: bool | None = None) -> dict | None:
    task = tasks_db.get(task_id)
    if not task:
        return None
    if title is not None:
        if not title.strip():
            raise ValueError("Title cannot be empty")
        task["title"] = title.strip()
    if completed is not None:
        task["completed"] = completed
    return task

def delete_task(task_id: int) -> bool:
    if task_id not in tasks_db:
        return False
    del tasks_db[task_id]
    return True

def clear_tasks():
    global tasks_db, _next_task_id
    tasks_db = {}
    _next_task_id = 1
