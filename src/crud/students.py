"""
CRUD operations for Students.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src import models

def get_student_by_student_id(db: Session, student_id: str) -> models.Student | None:
    """Fetches a student by their unique student ID."""
    return db.query(models.Student).filter(models.Student.student_id == student_id).first()

def get_student_by_tag_id(db: Session, tag_id: str) -> models.Student | None:
    """Fetches a student by their RFID tag ID."""
    return db.query(models.Student).filter(models.Student.tag_id == tag_id).first()

def get_all_students(db: Session, skip: int = 0, limit: int = 100) -> list[models.Student]:
    """Fetches all students with pagination."""
    return db.query(models.Student).offset(skip).limit(limit).all()

def create_student(db: Session, student: models.StudentCreate) -> models.Student:
    """Creates a new student in the database."""
    db_student = get_student_by_student_id(db, student.student_id)
    if db_student:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student with ID '{student.student_id}' already exists."
        )
    
    new_student = models.Student(**student.model_dump())
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

def update_student_tag_id(db: Session, student_id: str, tag_id: str) -> models.Student:
    """Updates the RFID tag ID for a specific student."""
    db_student = get_student_by_student_id(db, student_id)
    if not db_student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    
    existing_tag_user = get_student_by_tag_id(db, tag_id)
    if existing_tag_user and existing_tag_user.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag ID '{tag_id}' is already assigned to another student."
        )

    db_student.tag_id = tag_id
    db.commit()
    db.refresh(db_student)
    return db_student

def delete_student(db: Session, student_id: str) -> models.Student:
    """
    Deletes a student and all of their associated clearance records.
    
    This function first finds the student, then deletes all related rows in the
    'clearance_statuses' table before finally deleting the student record
    to maintain database integrity.
    """
    student_to_delete = get_student_by_student_id(db, student_id)
    if not student_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID '{student_id}' not found."
        )

    # First, delete all associated clearance statuses for this student.
    # This is crucial to prevent foreign key constraint violations.
    db.query(models.ClearanceStatus).filter(
        models.ClearanceStatus.student_id == student_id
    ).delete(synchronize_session=False)

    # Now, delete the student record itself.
    db.delete(student_to_delete)
    db.commit()
    
    return student_to_delete
