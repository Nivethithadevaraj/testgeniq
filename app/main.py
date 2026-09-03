from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

from app.tasks import create_task, get_all_tasks, get_task_by_id, update_task, delete_task
from app.auth import register_user, login_user, get_user, deactivate_user

app = FastAPI(title="TestGenIQ Target API", version="1.0.0")

ERROR_400 = {"description": "Business validation error"}
ERROR_404 = {"description": "Resource not found"}
ERROR_422 = {"description": "Request validation error"}

class TaskCreate(BaseModel):
    title: str = Field(..., examples=["Prepare release"])
    description: str = Field("", examples=["Regression testing"])
    priority: str = Field("medium", examples=["high"])

class TaskUpdate(BaseModel):
    title: str | None = Field(None, examples=["Updated task"])
    completed: bool | None = Field(None, examples=[True])

class UserRegister(BaseModel):
    username: str = Field(..., examples=["testuser"])
    password: str = Field(..., examples=["password123"])

class UserLogin(BaseModel):
    username: str = Field(..., examples=["testuser"])
    password: str = Field(..., examples=["password123"])

@app.get("/")
def root():
    return {"application": "TestGenIQ Target API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/tasks", responses={400: ERROR_400})
def api_create_task(request: TaskCreate):
    try:
        return create_task(request.title, request.description, request.priority)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/tasks")
def api_get_tasks():
    return get_all_tasks()

@app.get("/tasks/{task_id}", responses={404: ERROR_404})
def api_get_task(task_id: int = Path(..., examples=[1])):
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", responses={400: ERROR_400, 404: ERROR_404})
def api_update_task(request: TaskUpdate, task_id: int = Path(..., examples=[1])):
    try:
        task = update_task(task_id, request.title, request.completed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/tasks/{task_id}", responses={404: ERROR_404})
def api_delete_task(task_id: int = Path(..., examples=[1])):
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}

@app.post("/auth/register", responses={400: ERROR_400})
def api_register(request: UserRegister):
    try:
        return register_user(request.username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/auth/login", responses={400: ERROR_400})
def api_login(request: UserLogin):
    try:
        return login_user(request.username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/users/{username}", responses={404: ERROR_404})
def api_get_user(username: str = Path(..., examples=["testuser"])):
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users/{username}/deactivate", responses={404: ERROR_404})
def api_deactivate_user(username: str = Path(..., examples=["testuser"])):
    if not deactivate_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, "deactivated": True}
