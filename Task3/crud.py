from sqlalchemy.orm import Session
from .models import Student
from .database import SessionLocal
import csv


class StudentService:

    def __init__(self):
        self.db = SessionLocal()

    def add_student(self, last_name, first_name, faculty, course, grade):
        student = Student(
            last_name=last_name,
            first_name=first_name,
            faculty=faculty,
            course=course,
            grade=grade
        )
        self.db.add(student)
        self.db.commit()

    def get_students_by_faculty(self, faculty_name):
        return self.db.query(Student).filter(Student.faculty == faculty_name).all()

    # Получить уникальные курсы
    def get_unique_courses(self):
        return self.db.query(Student.course).distinct().all()

    def get_average_grade_by_faculty(self, faculty_name):
        from sqlalchemy import func
        return self.db.query(func.avg(Student.grade)).filter(
            Student.faculty == faculty_name
        ).scalar()

    def load_from_csv(self, filename):
        with open(filename, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.add_student(
                    row["Фамилия"].strip(),
                    row["Имя"].strip(),
                    row["Факультет"].strip(),
                    row["Курс"].strip(),
                    int(row["Оценка"])
                )