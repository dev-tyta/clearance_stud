from sqlmodel import Session, select
from typing import List, Optional

from src.models import Student, ClearanceStatus, ClearanceUpdate, Department, ClearanceProcess

def get_clearance_status_for_student(db: Session, student: Student) -> List[ClearanceStatus]:
    """
    Retrieves all clearance statuses for a given student object.
    """
    return student.clearance_statuses

def update_clearance_status(db: Session, clearance_update: ClearanceUpdate) -> Optional[ClearanceStatus]:
    """
    Updates the clearance status for a student in a specific department.

    This function performs a direct lookup on the ClearanceStatus table, which is
    more efficient than fetching the student and iterating through their statuses.
    """
    # First, find the student to ensure they exist.
    student = db.exec(select(Student).where(Student.matric_no == clearance_update.matric_no)).first()
    if not student:
        return None # Student not found

    # Directly query for the specific clearance status record.
    statement = select(ClearanceStatus).where(
        ClearanceStatus.student_id == student.id,
        ClearanceStatus.department == clearance_update.department
    )
    status_to_update = db.exec(statement).first()

    if not status_to_update:
        # This case should theoretically not happen if students are created correctly,
        # but it's a good safeguard.
        return None 

    # Update the status and commit the change.
    status_to_update.status = clearance_update.status
    db.add(status_to_update)
    db.commit()
    db.refresh(status_to_update)
    
    return status_to_update

def is_student_fully_cleared(db: Session, matric_no: str) -> bool:
    """
    Checks if a student has been approved by all required departments.
    """
    student = db.exec(select(Student).where(Student.matric_no == matric_no)).first()
    if not student:
        return False # Or raise an error, depending on desired behavior

    # Check if any of the student's clearance statuses are NOT 'approved'.
    for status in student.clearance_statuses:
        if status.status != ClearanceProcess.APPROVED:
            return False
            
    # If the loop completes without returning, all statuses are approved.
    return True
