"""
CRUD operations for student Clearance Statuses.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src import models

def get_clearance_statuses_by_student_id(db: Session, student_id: str) -> list[models.ClearanceStatus]:
    """
    Fetches all existing clearance status records for a given student.
    """
    return db.query(models.ClearanceStatus).filter(models.ClearanceStatus.student_id == student_id).all()

def update_clearance_status(
    db: Session,
    student_id: str,
    department: models.ClearanceDepartment,
    new_status: models.ClearanceStatusEnum,
    remarks: str,
    cleared_by_user_id: int
) -> models.ClearanceStatus:
    """
    Updates or creates a clearance status for a student in a specific department.
    """
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID '{student_id}' not found."
        )

    existing_status = db.query(models.ClearanceStatus).filter(
        models.ClearanceStatus.student_id == student_id,
        models.ClearanceStatus.department == department
    ).first()

    if existing_status:
        existing_status.status = new_status
        existing_status.remarks = remarks
        existing_status.cleared_by = cleared_by_user_id
        db_status = existing_status
    else:
        db_status = models.ClearanceStatus(
            student_id=student_id,
            department=department,
            status=new_status,
            remarks=remarks,
            cleared_by=cleared_by_user_id
        )
        db.add(db_status)

    db.commit()
    db.refresh(db_status)
    return db_status

def delete_clearance_status(
    db: Session,
    student_id: str,
    department: models.ClearanceDepartment
) -> models.ClearanceStatus | None:
    """
    Deletes a specific clearance status record for a student.

    This effectively resets the status for that department to the default state.
    Returns the deleted object if found, otherwise returns None.
    """
    status_to_delete = db.query(models.ClearanceStatus).filter(
        models.ClearanceStatus.student_id == student_id,
        models.ClearanceStatus.department == department
    ).first()

    if status_to_delete:
        db.delete(status_to_delete)
        db.commit()

    return status_to_delete


def get_all_clearance_status(db: Session) -> list[models.ClearanceStatus]:
    """
    Retrieves all clearance statuses from the database.
    
    This function is useful for administrative purposes, allowing staff to view
    all clearance records across all students and departments.
    """
    return db.query(models.ClearanceStatus).all()

def get_student_clearance_status(
    db: Session,
    student_id: str,
    department: models.ClearanceDepartment
) -> models.ClearanceStatus | None:
    """
    Retrieves the clearance status for a specific student in a specific department.
    
    Returns None if no status exists for that student and department.
    """
    return db.query(models.ClearanceStatus).filter(
        models.ClearanceStatus.student_id == student_id,
        models.ClearanceStatus.department == department
    ).first()