# ORM-based CRUD operations
# All functions are now synchronous and expect a SQLAlchemy Session

from sqlalchemy.orm import Session as SQLAlchemySessionType
from sqlalchemy import func, and_ # Add other SQLAlchemy functions as needed
from datetime import datetime, timedelta
import secrets
import bcrypt
from fastapi import HTTPException, status
from typing import List, Optional, Union # Added Union

from src import models # ORM models and Pydantic models
from src.database import initialize_student_clearance_statuses_orm # ORM based init

# --- Password Hashing ---
def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password_str: str) -> bool:
    """Verifies a plain password against a hashed password."""
    if not plain_password or not hashed_password_str:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_str.encode('utf-8'))

# --- Tag Uniqueness Checks (ORM) ---
def is_tag_id_unique_for_student(db: SQLAlchemySessionType, tag_id: str, exclude_student_pk: Optional[int] = None) -> bool:
    """Checks if tag_id is unique among students, optionally excluding one by PK."""
    query = db.query(models.Student).filter(models.Student.tag_id == tag_id)
    if exclude_student_pk:
        query = query.filter(models.Student.id != exclude_student_pk)
    return query.first() is None

def is_tag_id_unique_for_user(db: SQLAlchemySessionType, tag_id: str, exclude_user_pk: Optional[int] = None) -> bool:
    """Checks if tag_id is unique among users, optionally excluding one by PK."""
    query = db.query(models.User).filter(models.User.tag_id == tag_id)
    if exclude_user_pk:
        query = query.filter(models.User.id != exclude_user_pk)
    return query.first() is None

def check_tag_id_globally_unique_for_target(
    db: SQLAlchemySessionType,
    tag_id: str,
    target_type: models.TargetUserType,
    target_pk: Optional[int] = None # PK of the student or user being assigned the tag
) -> None:
    """
    Raises HTTPException if tag_id is not globally unique, excluding the target if provided.
    """
    if target_type == models.TargetUserType.STUDENT:
        if not is_tag_id_unique_for_student(db, tag_id, exclude_student_pk=target_pk):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tag ID '{tag_id}' is already assigned to another student.")
        if not is_tag_id_unique_for_user(db, tag_id): # Check against all users
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tag ID '{tag_id}' is already assigned to a user.")
    elif target_type == models.TargetUserType.STAFF_ADMIN:
        if not is_tag_id_unique_for_user(db, tag_id, exclude_user_pk=target_pk):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tag ID '{tag_id}' is already assigned to another user.")
        if not is_tag_id_unique_for_student(db, tag_id): # Check against all students
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tag ID '{tag_id}' is already assigned to a student.")


# --- Student CRUD (ORM) ---
def create_student(db: SQLAlchemySessionType, student_data: models.StudentCreate) -> models.Student:
    """Creates a new student    # No explicit database disconnect is needed here if using get_db dependency,
    # as sessions are managed per request.
    # If you had a global async engine (like from `databases` library previously),
    # you would disconnect it here.
 record using ORM."""
    existing_student_by_id = db.query(models.Student).filter(models.Student.student_id == student_data.student_id).first()
    if existing_student_by_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID already registered")

    if student_data.email:
        existing_student_by_email = db.query(models.Student).filter(models.Student.email == student_data.email).first()
        if existing_student_by_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if student_data.tag_id:
        check_tag_id_globally_unique_for_target(db, student_data.tag_id, models.TargetUserType.STUDENT)

    db_student = models.Student(
        student_id=student_data.student_id,
        name=student_data.name,
        email=student_data.email,
        department=student_data.department,
        tag_id=student_data.tag_id,
        created_at=datetime.utcnow()
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    initialize_student_clearance_statuses_orm(db, db_student.student_id)
    return db_student

def get_all_students(db: SQLAlchemySessionType, skip: int = 0, limit: int = 100) -> List[models.Student]:
    return db.query(models.Student).offset(skip).limit(limit).all()

def get_student_by_pk(db: SQLAlchemySessionType, student_pk: int) -> Optional[models.Student]:
    return db.query(models.Student).filter(models.Student.id == student_pk).first()

def get_student_by_student_id(db: SQLAlchemySessionType, student_id: str) -> Optional[models.Student]:
    return db.query(models.Student).filter(models.Student.student_id == student_id).first()

def get_student_by_tag_id(db: SQLAlchemySessionType, tag_id: str) -> Optional[models.Student]:
    return db.query(models.Student).filter(models.Student.tag_id == tag_id).first()

def update_student_tag_id(db: SQLAlchemySessionType, student_id_str: str, new_tag_id: str) -> models.Student:
    student = get_student_by_student_id(db, student_id_str)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    
    if student.tag_id == new_tag_id: # No change needed
        return student

    check_tag_id_globally_unique_for_target(db, new_tag_id, models.TargetUserType.STUDENT, target_pk=student.id)
    
    student.tag_id = new_tag_id
    student.updated_at = datetime.utcnow() # Assuming Student model has updated_at
    db.commit()
    db.refresh(student)
    return student

# --- User (Staff/Admin) CRUD (ORM) ---
def create_user(db: SQLAlchemySessionType, user_data: models.UserCreate) -> models.User:
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    if user_data.tag_id:
        check_tag_id_globally_unique_for_target(db, user_data.tag_id, models.TargetUserType.STAFF_ADMIN)

    hashed_pass = hash_password(user_data.password)
    db_user = models.User(
        username=user_data.username,
        hashed_password=hashed_pass,
        role=user_data.role,
        department=user_data.department,
        tag_id=user_data.tag_id,
        is_active=user_data.is_active if user_data.is_active is not None else True,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_pk(db: SQLAlchemySessionType, user_pk: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_pk).first()
    
def get_user_by_username(db: SQLAlchemySessionType, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_tag_id(db: SQLAlchemySessionType, tag_id: str) -> Optional[models.User]:
    # Also ensures user is active when fetching by tag for auth purposes
    return db.query(models.User).filter(models.User.tag_id == tag_id, models.User.is_active == True).first()

def update_user_tag_id(db: SQLAlchemySessionType, username_str: str, new_tag_id: str) -> models.User:
    user = get_user_by_username(db, username_str)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update tag for an inactive user.")

    if user.tag_id == new_tag_id: # No change needed
        return user

    check_tag_id_globally_unique_for_target(db, new_tag_id, models.TargetUserType.STAFF_ADMIN, target_pk=user.id)
        
    user.tag_id = new_tag_id
    user.updated_at = datetime.utcnow() # Assuming User model has updated_at
    db.commit()
    db.refresh(user)
    return user

# --- Clearance Status CRUD (ORM) ---
def create_or_update_clearance_status(
    db: SQLAlchemySessionType,
    status_data: models.ClearanceStatusCreate,
    cleared_by_user_pk: Optional[int] = None
) -> models.ClearanceStatus:
    
    existing_status = db.query(models.ClearanceStatus).filter(
        models.ClearanceStatus.student_id == status_data.student_id,
        models.ClearanceStatus.department == status_data.department
    ).first()

    current_time = datetime.utcnow()

    if existing_status:
        existing_status.status = status_data.status
        existing_status.remarks = status_data.remarks
        existing_status.cleared_by = cleared_by_user_pk
        existing_status.updated_at = current_time
        db_model = existing_status
    else:
        db_model = models.ClearanceStatus(
            student_id=status_data.student_id,
            department=status_data.department,
            status=status_data.status,
            remarks=status_data.remarks,
            cleared_by=cleared_by_user_pk,
            created_at=current_time,
            updated_at=current_time
        )
        db.add(db_model)
    
    db.commit()
    db.refresh(db_model)
    return db_model

def get_clearance_statuses_by_student_id(db: SQLAlchemySessionType, student_id_str: str) -> List[models.ClearanceStatus]:
    return db.query(models.ClearanceStatus).filter(models.ClearanceStatus.student_id == student_id_str).all()

# --- Device CRUD (ORM) ---
def create_device(db: SQLAlchemySessionType, device_data: models.DeviceCreateAdmin) -> models.Device:
    """Admin creates a device record."""
    if device_data.device_id: # ESP32 hardware ID
        existing_device_hw_id = db.query(models.Device).filter(models.Device.device_id == device_data.device_id).first()
        if existing_device_hw_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Device with hardware ID '{device_data.device_id}' already exists.")

    api_key = secrets.token_urlsafe(32)
    db_device = models.Device(
        name=device_data.name,
        description=device_data.description,
        api_key=api_key,
        device_id=device_data.device_id,
        location=device_data.location,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def register_device_esp(db: SQLAlchemySessionType, device_data: models.DeviceRegister) -> models.Device:
    """ESP32 self-registers or re-registers."""
    api_key = secrets.token_urlsafe(32)
    current_time = datetime.utcnow()

    existing_device = db.query(models.Device).filter(models.Device.device_id == device_data.device_id).first()

    if existing_device:
        existing_device.location = device_data.location
        existing_device.api_key = api_key # Consider policy: re-issue API key or keep old? Re-issuing.
        existing_device.last_seen = current_time
        existing_device.updated_at = current_time
        existing_device.is_active = True # Ensure device is active on registration
        db_model = existing_device
    else:
        db_model = models.Device(
            device_id=device_data.device_id, # Hardware ID from ESP
            location=device_data.location,
            api_key=api_key,
            is_active=True,
            last_seen=current_time,
            created_at=current_time,
            updated_at=current_time
            # name, description can be set by admin later
        )
        db.add(db_model)
    
    db.commit()
    db.refresh(db_model)
    return db_model

def get_device_by_pk(db: SQLAlchemySessionType, device_pk: int) -> Optional[models.Device]:
    return db.query(models.Device).filter(models.Device.id == device_pk).first()

def get_device_by_api_key(db: SQLAlchemySessionType, api_key: str) -> Optional[models.Device]:
    # For authentication, ensure device is active
    return db.query(models.Device).filter(models.Device.api_key == api_key).first()


def get_device_by_hardware_id(db: SQLAlchemySessionType, hardware_id: str) -> Optional[models.Device]:
    return db.query(models.Device).filter(models.Device.device_id == hardware_id).first()

def get_all_devices(db: SQLAlchemySessionType, skip: int = 0, limit: int = 100) -> List[models.Device]:
    return db.query(models.Device).offset(skip).limit(limit).all()

def update_device_last_seen(db: SQLAlchemySessionType, device_pk: int):
    device = get_device_by_pk(db, device_pk)
    if device:
        device.last_seen = datetime.utcnow()
        device.updated_at = datetime.utcnow()
        db.commit()

# --- Device Log CRUD (ORM) ---
def create_device_log(
    db: SQLAlchemySessionType,
    device_pk: Optional[int], # PK of the device in 'devices' table
    action: str,
    scanned_tag_id: Optional[str] = None,
    user_type: Optional[str] = "unknown",
    actual_device_id_str: Optional[str] = None # Hardware ID string from ESP
):
    db_log = models.DeviceLog(
        device_fk_id=device_pk,
        actual_device_id_str=actual_device_id_str,
        tag_id_scanned=scanned_tag_id,
        user_type=user_type,
        action=action,
        timestamp=datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    # No db.refresh(db_log) typically needed for logs unless you need its generated ID immediately.
    return db_log


# --- Pending Tag Link CRUD (ORM) ---
def create_pending_tag_link(
    db: SQLAlchemySessionType,
    device_pk: int,
    target_user_type: models.TargetUserType,
    target_identifier: str, # student_id or username
    initiated_by_user_pk: int,
    expires_in_minutes: int = 5
) -> models.PendingTagLink:
    
    device = get_device_by_pk(db, device_pk)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device with PK {device_pk} not found.")
    if not device.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Device '{device.name or device.device_id}' is not active.")

    # Check target validity
    if target_user_type == models.TargetUserType.STUDENT:
        student_target = get_student_by_student_id(db, target_identifier)
        if not student_target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target student with ID '{target_identifier}' not found.")
        if student_target.tag_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Student '{target_identifier}' already has a tag linked.")
    elif target_user_type == models.TargetUserType.STAFF_ADMIN:
        user_target = get_user_by_username(db, target_identifier)
        if not user_target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target user with username '{target_identifier}' not found.")
        if not user_target.is_active:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target user '{target_identifier}' is not active.")
        if user_target.tag_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User '{target_identifier}' already has a tag linked.")
    else: # Should be caught by Pydantic if an invalid enum is passed
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target user type provided.")

    # Check for existing active pending link for this device
    existing_link = db.query(models.PendingTagLink).filter(
        models.PendingTagLink.device_id_fk == device_pk,
        models.PendingTagLink.expires_at > datetime.utcnow()
    ).first()
    if existing_link:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Device '{device.name or device.device_id}' is already awaiting a tag scan.")

    expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    db_pending_link = models.PendingTagLink(
        device_id_fk=device_pk,
        target_user_type=target_user_type,
        target_identifier=target_identifier,
        initiated_by_user_id=initiated_by_user_pk,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(db_pending_link)
    db.commit()
    db.refresh(db_pending_link)
    return db_pending_link

def get_active_pending_tag_link_by_device_pk(db: SQLAlchemySessionType, device_pk: int) -> Optional[models.PendingTagLink]:
    return db.query(models.PendingTagLink).filter(
        models.PendingTagLink.device_id_fk == device_pk,
        models.PendingTagLink.expires_at > datetime.utcnow()
    ).order_by(models.PendingTagLink.created_at.desc()).first() # Get the latest if multiple somehow exist (shouldn't)

def delete_pending_tag_link(db: SQLAlchemySessionType, pending_link_pk: int):
    link = db.query(models.PendingTagLink).filter(models.PendingTagLink.id == pending_link_pk).first()
    if link:
        db.delete(link)
        db.commit()
