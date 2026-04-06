from typing import Annotated
from fastapi import FastAPI, APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .crud import StudentService
from .models import User

app = FastAPI()

Base.metadata.create_all(bind=engine)

service = StudentService()
active_sessions: set[int] = set()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth(
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None
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


auth_router = APIRouter(prefix="/auth", tags=["auth"])


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
    return {"message": "Students API is working"}


# LOAD CSV
@app.get("/load")
def load_data(current_user_id: int = Depends(require_auth)):
    service.load_from_csv("Task3/students.csv")
    return {"message": "Data loaded successfully"}


# CREATE
@app.post("/students")
def create_student(student: dict, current_user_id: int = Depends(require_auth)):
    new_student = service.add_student(
        student["last_name"],
        student["first_name"],
        student["faculty"],
        student["course"],
        student["grade"]
    )

    return {
        "id": new_student.id,
        "last_name": new_student.last_name,
        "first_name": new_student.first_name,
        "faculty": new_student.faculty,
        "course": new_student.course,
        "grade": new_student.grade
    }


# READ ALL
@app.get("/students")
def get_students(current_user_id: int = Depends(require_auth)):
    students = service.get_all_students()

    return [
        {
            "id": s.id,
            "last_name": s.last_name,
            "first_name": s.first_name,
            "faculty": s.faculty,
            "course": s.course,
            "grade": s.grade
        }
        for s in students
    ]


# READ ONE
@app.get("/students/{student_id}")
def get_student(student_id: int, current_user_id: int = Depends(require_auth)):
    student = service.get_student(student_id)

    if not student:
        return {"error": "Student not found"}

    return {
        "id": student.id,
        "last_name": student.last_name,
        "first_name": student.first_name,
        "faculty": student.faculty,
        "course": student.course,
        "grade": student.grade
    }


# UPDATE
@app.put("/students/{student_id}")
def update_student(
    student_id: int,
    student: dict,
    current_user_id: int = Depends(require_auth),
):

    updated = service.update_student(
        student_id,
        student["last_name"],
        student["first_name"],
        student["faculty"],
        student["course"],
        student["grade"]
    )

    if not updated:
        return {"error": "Student not found"}

    return {"message": "Student updated"}


# DELETE
@app.delete("/students/{student_id}")
def delete_student(student_id: int, current_user_id: int = Depends(require_auth)):
    result = service.delete_student(student_id)

    if not result:
        return {"error": "Student not found"}

    return result


# OLD ENDPOINTS FROM PREVIOUS HW
@app.get("/faculty/{faculty_name}")
def students_by_faculty(
    faculty_name: str,
    current_user_id: int = Depends(require_auth),
):
    students = service.get_students_by_faculty(faculty_name)

    return [
        {
            "id": s.id,
            "last_name": s.last_name,
            "first_name": s.first_name,
            "faculty": s.faculty,
            "course": s.course,
            "grade": s.grade
        }
        for s in students
    ]


@app.get("/courses")
def unique_courses(current_user_id: int = Depends(require_auth)):
    courses = service.get_unique_courses()
    return [course[0] for course in courses]


@app.get("/average/{faculty_name}")
def average_grade(
    faculty_name: str,
    current_user_id: int = Depends(require_auth),
):
    avg = service.get_average_grade_by_faculty(faculty_name)

    return {
        "faculty": faculty_name,
        "average_grade": avg
    }
