from fastapi import FastAPI
from .database import engine, Base
from .crud import StudentService
import os
app = FastAPI()

Base.metadata.create_all(bind=engine)

service = StudentService()

@app.get("/")
def read_root():
    return {"message": "Students API is working"}

@app.get("/load")
def load_data():
    service.load_from_csv("Task3/students.csv")
    return {"message": "Data loaded successfully"}

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

# -------------------------------
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