from fastapi import FastAPI
from .database import engine, Base
from .crud import StudentService

app = FastAPI()

Base.metadata.create_all(bind=engine)

service = StudentService()


@app.get("/")
def read_root():
    return {"message": "Students API is working"}


# LOAD CSV
@app.get("/load")
def load_data():
    service.load_from_csv("Task3/students.csv")
    return {"message": "Data loaded successfully"}


# CREATE
@app.post("/students")
def create_student(student: dict):
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
def get_students():
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
def get_student(student_id: int):
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
def update_student(student_id: int, student: dict):

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
def delete_student(student_id: int):
    result = service.delete_student(student_id)

    if not result:
        return {"error": "Student not found"}

    return result


# OLD ENDPOINTS FROM PREVIOUS HW
@app.get("/faculty/{faculty_name}")
def students_by_faculty(faculty_name: str):
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
def unique_courses():
    courses = service.get_unique_courses()
    return [course[0] for course in courses]


@app.get("/average/{faculty_name}")
def average_grade(faculty_name: str):
    avg = service.get_average_grade_by_faculty(faculty_name)

    return {
        "faculty": faculty_name,
        "average_grade": avg
    }