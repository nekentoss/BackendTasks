import json
import os
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .crud import StudentService
from .database import Base, SessionLocal, engine
from .models import User

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

app = FastAPI()

Base.metadata.create_all(bind=engine)

service = StudentService()
active_sessions: set[int] = set()
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def create_redis_client():
    if redis is None:
        return None
    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


redis_client = create_redis_client()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth(
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: pass X-User-Id header",
        )
    if x_user_id not in active_sessions:
        raise HTTPException(status_code=401, detail="User session is not active")
    return x_user_id


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class StudentPayload(BaseModel):
    last_name: str
    first_name: str
    faculty: str
    course: str
    grade: int


class CsvLoadRequest(BaseModel):
    file_path: str


class DeleteStudentsRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)


auth_router = APIRouter(prefix="/auth", tags=["auth"])


def serialize_student(student):
    return {
        "id": student.id,
        "last_name": student.last_name,
        "first_name": student.first_name,
        "faculty": student.faculty,
        "course": student.course,
        "grade": student.grade,
    }


def cache_get(key: str):
    if not redis_client:
        return None
    raw = redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value):
    if not redis_client:
        return
    redis_client.setex(key, CACHE_TTL_SECONDS, json.dumps(value, ensure_ascii=False))


def invalidate_students_cache():
    if not redis_client:
        return
    keys = redis_client.keys("students:*")
    if keys:
        redis_client.delete(*keys)


def load_from_csv_task(file_path: str):
    service.load_from_csv(file_path)
    invalidate_students_cache()


def delete_students_task(student_ids: list[int]):
    service.delete_students_by_ids(student_ids)
    invalidate_students_cache()


@auth_router.post("/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=payload.username, password=payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered", "user_id": user.id}


@auth_router.post("/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.username == payload.username,
            User.password == payload.password,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    active_sessions.add(user.id)
    return {"message": "Login successful", "user_id": user.id}


@auth_router.post("/logout")
def logout_user(current_user_id: int = Depends(require_auth)):
    active_sessions.discard(current_user_id)
    return {"message": "Logout successful"}


app.include_router(auth_router)


@app.get("/")
def read_root(current_user_id: int = Depends(require_auth)):
    cache_key = "students:root"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    result = {"message": "Students API is working"}
    cache_set(cache_key, result)
    return result


@app.post("/tasks/load-csv", status_code=status.HTTP_202_ACCEPTED)
def load_data_in_background(
    payload: CsvLoadRequest,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(require_auth),
):
    if not os.path.isfile(payload.file_path):
        raise HTTPException(status_code=404, detail="CSV file not found")

    background_tasks.add_task(load_from_csv_task, payload.file_path)
    return {
        "message": "CSV loading started in background",
        "file_path": payload.file_path,
    }


@app.post("/tasks/delete-students", status_code=status.HTTP_202_ACCEPTED)
def delete_students_in_background(
    payload: DeleteStudentsRequest,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(require_auth),
):
    background_tasks.add_task(delete_students_task, payload.student_ids)
    return {
        "message": "Students deletion started in background",
        "student_ids": payload.student_ids,
    }


@app.post("/students")
def create_student(student: StudentPayload, current_user_id: int = Depends(require_auth)):
    new_student = service.add_student(
        student.last_name,
        student.first_name,
        student.faculty,
        student.course,
        student.grade,
    )
    invalidate_students_cache()
    return serialize_student(new_student)


@app.get("/students")
def get_students(current_user_id: int = Depends(require_auth)):
    cache_key = "students:all"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    students = service.get_all_students()
    result = [serialize_student(s) for s in students]
    cache_set(cache_key, result)
    return result


@app.get("/students/{student_id}")
def get_student(student_id: int, current_user_id: int = Depends(require_auth)):
    cache_key = f"students:item:{student_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    student = service.get_student(student_id)
    if not student:
        return {"error": "Student not found"}

    result = serialize_student(student)
    cache_set(cache_key, result)
    return result


@app.put("/students/{student_id}")
def update_student(
    student_id: int,
    student: StudentPayload,
    current_user_id: int = Depends(require_auth),
):
    updated = service.update_student(
        student_id,
        student.last_name,
        student.first_name,
        student.faculty,
        student.course,
        student.grade,
    )

    if not updated:
        return {"error": "Student not found"}

    invalidate_students_cache()
    return {"message": "Student updated"}


@app.delete("/students/{student_id}")
def delete_student(student_id: int, current_user_id: int = Depends(require_auth)):
    result = service.delete_student(student_id)

    if not result:
        return {"error": "Student not found"}

    invalidate_students_cache()
    return result


@app.get("/faculty/{faculty_name}")
def students_by_faculty(
    faculty_name: str,
    current_user_id: int = Depends(require_auth),
):
    cache_key = f"students:faculty:{faculty_name.lower()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    students = service.get_students_by_faculty(faculty_name)
    result = [serialize_student(s) for s in students]
    cache_set(cache_key, result)
    return result


@app.get("/courses")
def unique_courses(current_user_id: int = Depends(require_auth)):
    cache_key = "students:courses"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    courses = service.get_unique_courses()
    result = [course[0] for course in courses]
    cache_set(cache_key, result)
    return result


@app.get("/average/{faculty_name}")
def average_grade(
    faculty_name: str,
    current_user_id: int = Depends(require_auth),
):
    cache_key = f"students:average:{faculty_name.lower()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    avg = service.get_average_grade_by_faculty(faculty_name)
    result = {"faculty": faculty_name, "average_grade": avg}
    cache_set(cache_key, result)
    return result
