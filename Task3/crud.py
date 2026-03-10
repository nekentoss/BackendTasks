from sqlalchemy.orm import Session
from .models import Student
from .database import SessionLocal
import csv


class StudentService:

    def __init__(self):
        self.db = SessionLocal()

    # CREATE
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
        self.db.refresh(student)
        return student

    # READ ALL
    def get_all_students(self):
        return self.db.query(Student).all()

    # READ ONE
    def get_student(self, student_id):
        return self.db.query(Student).filter(Student.id == student_id).first()

    # READ by faculty
    def get_students_by_faculty(self, faculty_name):
        return self.db.query(Student).filter(Student.faculty == faculty_name).all()

    # UNIQUE COURSES
    def get_unique_courses(self):
        return self.db.query(Student.course).distinct().all()

    # AVERAGE GRADE
    def get_average_grade_by_faculty(self, faculty_name):
        from sqlalchemy import func
        return self.db.query(func.avg(Student.grade)).filter(
            Student.faculty == faculty_name
        ).scalar()

    # UPDATE
    def update_student(self, student_id, last_name, first_name, faculty, course, grade):
        student = self.db.query(Student).filter(Student.id == student_id).first()

        if not student:
            return None

        student.last_name = last_name
        student.first_name = first_name
        student.faculty = faculty
        student.course = course
        student.grade = grade

        self.db.commit()
        self.db.refresh(student)

        return student

    # DELETE
    def delete_student(self, student_id):
        student = self.db.query(Student).filter(Student.id == student_id).first()

        if not student:
            return None

        self.db.delete(student)
        self.db.commit()

        return {"message": "Student deleted"}

    # LOAD CSV
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