from contextlib import contextmanager
from pathlib import Path
import csv

from .models import Student
from .database import SessionLocal


class StudentService:
    def __init__(self):
        self.session_factory = SessionLocal

    @contextmanager
    def _session_scope(self):
        db = self.session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # CREATE
    def add_student(self, last_name, first_name, faculty, course, grade):
        with self._session_scope() as db:
            student = Student(
                last_name=last_name,
                first_name=first_name,
                faculty=faculty,
                course=course,
                grade=grade,
            )
            db.add(student)
            db.flush()
            db.refresh(student)
            return student

    # READ ALL
    def get_all_students(self):
        with self._session_scope() as db:
            return db.query(Student).all()

    # READ ONE
    def get_student(self, student_id):
        with self._session_scope() as db:
            return db.query(Student).filter(Student.id == student_id).first()

    # READ by faculty
    def get_students_by_faculty(self, faculty_name):
        with self._session_scope() as db:
            return db.query(Student).filter(Student.faculty == faculty_name).all()

    # UNIQUE COURSES
    def get_unique_courses(self):
        with self._session_scope() as db:
            return db.query(Student.course).distinct().all()

    # AVERAGE GRADE
    def get_average_grade_by_faculty(self, faculty_name):
        from sqlalchemy import func

        with self._session_scope() as db:
            return (
                db.query(func.avg(Student.grade))
                .filter(Student.faculty == faculty_name)
                .scalar()
            )

    # UPDATE
    def update_student(self, student_id, last_name, first_name, faculty, course, grade):
        with self._session_scope() as db:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return None

            student.last_name = last_name
            student.first_name = first_name
            student.faculty = faculty
            student.course = course
            student.grade = grade

            db.flush()
            db.refresh(student)
            return student

    # DELETE
    def delete_student(self, student_id):
        with self._session_scope() as db:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return None

            db.delete(student)
            return {"message": "Student deleted"}

    def delete_students_by_ids(self, student_ids):
        unique_ids = list(set(student_ids))
        with self._session_scope() as db:
            deleted_count = (
                db.query(Student)
                .filter(Student.id.in_(unique_ids))
                .delete(synchronize_session=False)
            )
            return deleted_count

    # LOAD CSV
    def load_from_csv(self, filename):
        csv_path = Path(filename)
        if not csv_path.exists() or not csv_path.is_file():
            raise FileNotFoundError(f"CSV file not found: {filename}")

        last_error = None
        for encoding in ("utf-8-sig", "cp1251", "utf-8"):
            try:
                with open(csv_path, encoding=encoding, newline="") as file:
                    rows = list(csv.reader(file))
                break
            except UnicodeDecodeError as exc:
                last_error = exc
                rows = None
        else:
            raise UnicodeDecodeError(
                "csv", b"", 0, 1, f"Unable to decode CSV file: {last_error}"
            )

        if not rows:
            return 0

        loaded_count = 0
        data_rows = rows[1:] if len(rows) > 1 else []

        with self._session_scope() as db:
            for row in data_rows:
                if len(row) < 5:
                    continue

                try:
                    grade = int(row[4].strip())
                except (TypeError, ValueError):
                    continue

                student = Student(
                    last_name=row[0].strip(),
                    first_name=row[1].strip(),
                    faculty=row[2].strip(),
                    course=row[3].strip(),
                    grade=grade,
                )
                db.add(student)
                loaded_count += 1

        return loaded_count
