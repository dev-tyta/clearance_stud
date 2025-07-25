from sqlmodel import Session, select
from typing import List, Optional
from src.models import ClearanceStatus, Student, ClearanceUpdate, ClearanceStatusEnum

def get_clearance_status_for_student(db: Session, student: Student) -> List[ClearanceStatus]:
    """
    Retrieves all clearance statuses for a given student object.
    """
    return student.clearance_statuses

def update_clearance_status(db: Session, update_data: ClearanceUpdate) -> ClearanceStatus | None:
    """
    Updates the clearance status for a specific student and department.
    """
    # Find the student first
    student_statement = select(Student).where(Student.matric_no == update_data.matric_no)
    student = db.exec(student_statement).first()
    if not student:
        return None # Student not found

    # Now find the specific clearance status record for that student
    status_statement = select(ClearanceStatus).where(
        ClearanceStatus.student_id == student.id,
        ClearanceStatus.department == update_data.department
    )
    clearance_record = db.exec(status_statement).first()

    if not clearance_record:
        # This case should ideally not happen if students are created correctly
        return None 

    # Update the status and remarks
    clearance_record.status = update_data.status
    if update_data.remarks is not None:
        clearance_record.remarks = update_data.remarks
    
    db.add(clearance_record)
    db.commit()
    db.refresh(clearance_record)

    return clearance_record


def is_student_fully_cleared(db: Session, matric_no: str) -> bool:
    """
    Checks if a student has been approved by all required departments.
    """
    student = db.exec(select(Student).where(Student.matric_no == matric_no)).first()
    if not student:
        return False # Or raise an error, depending on desired behavior

    # Check if any of the student's clearance statuses are NOT 'approved'.
    for status in student.clearance_statuses:
        if status.status != ClearanceStatusEnum.APPROVED:
            return False
            
    # If the loop completes without returning, all statuses are approved.
    return True
