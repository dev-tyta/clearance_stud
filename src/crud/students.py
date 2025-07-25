from sqlmodel import Session, select
from typing import List, Optional

from src.models import (
    Student, StudentCreate, StudentUpdate, User, Role, ClearanceStatus, ClearanceDepartment, RFIDTag
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
def create_student(db: Session, student_data: StudentCreate) -> Student:
    """
    Creates a new student along with their associated user account for login
    and initializes their clearance statuses.
    """
    # 1. Create the associated User account for the student to log in
    # The student's username is their matriculation number.
    user_for_student = user_crud.UserCreate(
        username=student_data.matric_no,
        password=student_data.password,
        email=student_data.email,
        full_name=student_data.full_name,
        role=Role.STUDENT
    )
    # This might raise an exception if username/email exists, which is good.
    db_user = user_crud.create_user(db, user=user_for_student)

    # 2. Create the Student profile
    db_student = Student(
        full_name=student_data.full_name,
        matric_no=student_data.matric_no,
        email=student_data.email,
        department=student_data.department,
        # Note: The User linkage is handled via the RFID tag linking process
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    # 3. Initialize all clearance statuses for the new student
    for dept in ClearanceDepartment:
        status = ClearanceStatus(student_id=db_student.id, department=dept)
        db.add(status)
    
    db.commit()
    db.refresh(db_student)
    
    return db_student

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
