from sqlmodel import Session, select
from typing import List, Optional

from src.models import Student, StudentCreate, StudentUpdate, RFIDTag, ClearanceStatus, Department, ClearanceProcess
from src.auth import hash_password

# --- Read Operations ---

def get_student_by_id(db: Session, student_id: int) -> Optional[Student]:
    """Retrieves a student by their primary key ID."""
    return db.get(Student, student_id)

def get_student_by_matric_no(db: Session, matric_no: str) -> Optional[Student]:
    """Retrieves a student by their unique matriculation number."""
    return db.exec(select(Student).where(Student.matric_no == matric_no)).first()

def get_student_by_tag_id(db: Session, tag_id: str) -> Optional[Student]:
    """Retrieves a student by their linked RFID tag ID."""
    statement = select(Student).join(RFIDTag).where(RFIDTag.tag_id == tag_id)
    return db.exec(statement).first()

def get_all_students(db: Session, skip: int = 0, limit: int = 100) -> List[Student]:
    """Retrieves a paginated list of all students."""
    return db.exec(select(Student).offset(skip).limit(limit)).all()

# --- Write Operations ---

def create_student(db: Session, student: StudentCreate) -> Student:
    """
    Creates a new student and initializes their clearance statuses.

    This is a critical business logic function. When a student is created,
    this function automatically creates a 'pending' clearance record for every
    department defined in the `Department` enum.
    """
    hashed_pass = hash_password(student.password)
    db_student = Student(
        matric_no=student.matric_no,
        full_name=student.full_name,
        email=student.email,
        hashed_password=hashed_pass,
        # Department will be set from the StudentCreate model
        department=student.department 
    )
    
    # --- Auto-populate clearance statuses ---
    initial_statuses = []
    for dept in Department:
        status = ClearanceStatus(
            department=dept,
            status=ClearanceProcess.PENDING
        )
        initial_statuses.append(status)
    
    db_student.clearance_statuses = initial_statuses
    # --- End of auto-population ---

    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

def update_student(db: Session, student_id: int, student_update: StudentUpdate) -> Optional[Student]:
    """
    Updates a student's information.
    If a new password is provided, it will be hashed.
    """
    db_student = db.get(Student, student_id)
    if not db_student:
        return None

    update_data = student_update.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(db_student, key, value)
    
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

def delete_student(db: Session, student_id: int) -> Optional[Student]:
    """

    Deletes a student from the database.
    All associated clearance statuses and the linked RFID tag will also be 
    deleted automatically due to the cascade settings in the data models.
    """
    db_student = db.get(Student, student_id)
    if not db_student:
        return None
    
    db.delete(db_student)
    db.commit()
    return db_student
