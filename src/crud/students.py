from sqlmodel import Session, select
from typing import List, Optional

from src.models import (
    Student, StudentCreate, StudentUpdate, User, Role, ClearanceStatus, ClearanceDepartment, RFIDTag, UserCreate
)
from src.crud import users as user_crud
# --- Read Operations ---

def get_student_by_id(db: Session, student_id: int) -> Optional[Student]:
    """Retrieves a student by their primary key ID."""
    return db.get(Student, student_id)

def get_student_by_matric_no(db: Session, matric_no: str) -> Optional[Student]:
    """Retrieves a student by their unique matriculation number."""
    return db.exec(select(Student).where(Student.matric_no == matric_no)).first()

def get_student_by_tag_id(db: Session, tag_id: str) -> Optional[Student]:
    """Get student by RFID tag ID."""
    from src.models import RFIDTag
    tag = db.exec(select(RFIDTag).where(RFIDTag.tag_id == tag_id)).first()
    if tag and tag.student_id:
        return db.exec(select(Student).where(Student.id == tag.student_id)).first()
    return None

def get_all_students(db: Session, skip: int = 0, limit: int = 100) -> List[Student]:
    """Retrieves a paginated list of all students."""
    return db.exec(select(Student).offset(skip).limit(limit)).all()

# --- Write Operations ---
def create_student(db: Session, student: StudentCreate) -> Student:
    """
    Creates a new student record and automatically performs two key actions:
    1. Creates an associated User account for the student to enable login.
    2. Initializes all required clearance statuses, setting them to 'pending'.
    """
    # Step 1: Create the associated User account for login purposes.
    # The student's matriculation number is used as their username.
    user_for_student = StudentCreate(
        username=student.matric_no,
        password=student.password, # The password from the student creation form
        email=student.email,
        full_name=student.full_name,
        department=student.department,
        
        # role=Role.STUDENT # The role is always 'student'
    )
    user_crud.create_user(db, user=user_for_student) # Create the user

    # Step 2: Create the Student profile.
    db_student = Student.model_validate(student)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    # Step 3: Automatically create all necessary clearance status entries for the new student.
    for dept in ClearanceDepartment:
        status = ClearanceStatus(
            department=dept,
            student_id=db_student.id
        )
        db.add(status)
    
def update_student(db: Session, student: Student, updates: StudentUpdate) -> Student:
    """Updates a student's profile information."""
    student = get_student_by_id(db, student_id=student.id)
    if not student:
        return None
    
    update_data = updates.model_dump(exclude_unset=True)
    student.sqlmodel_update(update_data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

def delete_student(db: Session, student_id: int) -> Student | None:
    """Deletes a student and their associated clearance records."""
    student_to_delete = db.get(Student, student_id)
    if not student_to_delete:
        return None
    
    # Also delete the associated user account
    user_to_delete = user_crud.get_user_by_username(db, username=student_to_delete.matric_no)
    if user_to_delete:
        db.delete(user_to_delete)

    db.delete(student_to_delete)
    db.commit()
    return student_to_delete
