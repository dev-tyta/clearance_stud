import sqlalchemy
import os
from dotenv import load_dotenv
from datetime import datetime

# Import Enums, Base, and specific ORM models needed for initialization
from src.models import (
    UserRole, ClearanceDepartment, ClearanceStatusEnum, Base, TargetUserType,
    Student as StudentORM, # Alias to avoid confusion if Student Pydantic model is also imported
    ClearanceStatus as ClearanceStatusORM, # Alias for ORM model
    User as UserORM,
    Device as DeviceORM
)
from sqlalchemy.orm import Session as SQLAlchemySessionType

# Load environment variables from a .env file
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")

# Check if DATABASE_URL is set
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

# SQLAlchemy engine
engine = sqlalchemy.create_engine(DATABASE_URL)

metadata = Base.metadata

def create_db_tables():
    """Creates database tables based on SQLAlchemy ORM metadata."""
    try:
        print("Attempting to create database tables (if they don't exist)...")
        metadata.create_all(bind=engine) # Use Base.metadata from models.py
        print("Database tables creation attempt finished.")
    except Exception as e:
        print(f"Error during database table creation: {e}")
        print("Please ensure your database is accessible and the connection string is correct.")


# Initialize default clearance statuses for new students (Synchronous ORM version)
def initialize_student_clearance_statuses_orm(db: SQLAlchemySessionType, student_id_str: str):
    """
    Creates default clearance status entries for all departments for a new student.
    Uses SQLAlchemy ORM session.
    """
    created_rows_info = []
    student = db.query(StudentORM).filter(StudentORM.student_id == student_id_str).first()
    if not student:
        print(f"Warning: Student {student_id_str} not found when trying to initialize clearance statuses.")
        return

    for dept_enum_member in ClearanceDepartment: # Iterate through centralized Enum
        # Check if status already exists for this student and department
        existing_status = db.query(ClearanceStatusORM).filter(
            ClearanceStatusORM.student_id == student_id_str,
            ClearanceStatusORM.department == dept_enum_member
        ).first()

        if not existing_status:
            new_status = ClearanceStatusORM(
                student_id=student_id_str,
                department=dept_enum_member,
                status=ClearanceStatusEnum.NOT_COMPLETED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_status)
            created_rows_info.append({"department": dept_enum_member.value, "status": "initialized"})
        else:
            created_rows_info.append({"department": dept_enum_member.value, "status": "already_exists"})
    
    if created_rows_info:
        try:
            db.commit()
            print(f"Committed clearance statuses for student {student_id_str}: {created_rows_info}")
        except Exception as e:
            db.rollback()
            print(f"Error committing clearance statuses for student {student_id_str}: {e}")
            raise
    else:
        print(f"No new clearance statuses to initialize or commit for student {student_id_str}.")


from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency to get a SQLAlchemy database session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
