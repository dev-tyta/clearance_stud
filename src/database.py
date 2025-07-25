"""
This module handles database connection, session management, table creation,
and initial data seeding.
"""
import sqlalchemy
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySessionType
from datetime import datetime

# Import the centralized settings object
from src.config import settings 

# Import Enums, Base, and specific ORM models needed for initialization
from src.models import (
    Base,
    ClearanceDepartment,
    ClearanceStatusEnum,
    Student as StudentORM,
    ClearanceStatus as ClearanceStatusORM
)

# --- Database Engine Setup ---
# Create the SQLAlchemy engine using the URI from our secure settings.
engine = sqlalchemy.create_engine(
    settings.POSTGRES_URI,
    pool_pre_ping=True  # Helps prevent errors from stale connections
)

# --- Session Management ---
# Create a configured "Session" class. This is our session factory.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency that creates and yields a new database session
    for each request, and ensures it's closed afterward.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Database Initialization Functions ---

def create_db_and_tables():
    """
    Creates all database tables defined in `src/models.py` if they do not exist.
    This function should be called once on application startup.
    """
    try:
        print("Attempting to create database tables (if they don't exist)...")
        Base.metadata.create_all(bind=engine)
        print("Database tables are ready.")
    except Exception as e:
        print(f"FATAL: Error during database table creation: {e}")
        print("Please ensure your database is accessible and the POSTGRES_URI is correct.")
        # In a real production app, you might want to exit here if the DB is critical
        raise

def initialize_student_clearance_statuses(db: SQLAlchemySessionType, student_id_str: str):
    """
    Creates default 'NOT_COMPLETED' clearance status entries for all required
    departments for a newly created student. This ensures every student's
    clearance record is complete from the start.
    """
    student = db.query(StudentORM).filter(StudentORM.student_id == student_id_str).first()
    if not student:
        print(f"Warning: Student '{student_id_str}' not found when trying to initialize clearance statuses.")
        return

    for dept in ClearanceDepartment:
        # Check if a status for this department already exists
        exists = db.query(ClearanceStatusORM).filter(
            ClearanceStatusORM.student_id == student_id_str,
            ClearanceStatusORM.department == dept
        ).first()

        if not exists:
            # If it doesn't exist, create the default record
            new_status = ClearanceStatusORM(
                student_id=student_id_str,
                department=dept,
                status=ClearanceStatusEnum.NOT_COMPLETED
            )
            db.add(new_status)
    
    # Commit all the new statuses at once
    try:
        db.commit()
    except Exception as e:
        print(f"Error committing initial clearance statuses for student {student_id_str}: {e}")
        db.rollback()
        raise

# Alias for backward compatibility
initialize_student_clearance_statuses_orm = initialize_student_clearance_statuses