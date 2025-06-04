from src.database import (
    database, students, clearance_statuses, device_logs, devices, users,
    initialize_student_clearance_statuses, ClearanceStatusEnum, ClearanceDepartment
)
from src.models import (
    StudentCreate, ClearanceStatusCreate, TagScan, DeviceRegister, 
    UserCreate, ClearanceStatusUpdate, User, Student, Clearance, Device, PendingTagLink, TargetUserType
)
from sqlalchemy import select, insert, update, func, and_
from datetime import datetime, timedelta
import secrets
import bcrypt
from fastapi import HTTPException, status
from src import models
from typing import List, Optional

# --- CRUD operations for Students ---

async def create_student(student: StudentCreate):
    """Creates a new student record and initializes clearance statuses."""
    # Build an insert query using SQLAlchemy
    query = students.insert().values(
        student_id=student.student_id,
        name=student.name,
        department=student.department,
        tag_id=student.tag_id,
        created_at=datetime.utcnow()
    )
    # Execute the query asynchronously
    last_record_id = await database.execute(query)
    
    # Initialize default clearance statuses for all departments
    await initialize_student_clearance_statuses(student.student_id)
    
    # Return the created student data including the generated ID
    return {**student.dict(), "id": last_record_id, "created_at": datetime.utcnow()}

async def get_all_students():
    """Retrieves all student records from the database."""
    query = students.select()
    return await database.fetch_all(query)

async def get_student_by_student_id(student_id: str):
    """Retrieves a student record by their student ID."""
    query = students.select().where(students.c.student_id == student_id)
    return await database.fetch_one(query)

async def get_student_by_tag_id(tag_id: str):
    """Retrieves a student record by their tag ID."""
    query = students.select().where(students.c.tag_id == tag_id)
    return await database.fetch_one(query)

# --- CRUD operations for Users (Staff/Admin) ---

async def create_user(user: UserCreate):
    """Creates a new staff/admin user."""
    # Hash the password
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    
    query = users.insert().values(
        username=user.username,
        hashed_password=hashed_password.decode('utf-8'),
        role=user.role,
        department=user.department,
        tag_id=user.tag_id,
        created_at=datetime.utcnow()
    )
    
    last_record_id = await database.execute(query)
    return {
        "id": last_record_id,
        "username": user.username,
        "role": user.role,
        "department": user.department,
        "tag_id": user.tag_id,
        "created_at": datetime.utcnow()
    }

async def get_user_by_tag_id(tag_id: str):
    """Retrieves a user record by their tag ID."""
    query = users.select().where(users.c.tag_id == tag_id)
    return await database.fetch_one(query)

async def get_user_by_username(username: str):
    """Retrieves a user record by username."""
    query = users.select().where(users.c.username == username)
    return await database.fetch_one(query)

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- CRUD operations for Clearance Statuses ---

async def create_or_update_clearance_status(status_data: ClearanceStatusCreate, cleared_by_user_id: int = None):
    """Creates a new clearance status or updates an existing one."""
    # Check if clearance status already exists for this student and department
    query = select(clearance_statuses).where(
        (clearance_statuses.c.student_id == status_data.student_id) &
        (clearance_statuses.c.department == status_data.department)
    )
    existing_status = await database.fetch_one(query)

    current_time = datetime.utcnow()

    if existing_status:
        # Update existing status
        query = update(clearance_statuses).where(
            (clearance_statuses.c.student_id == status_data.student_id) &
            (clearance_statuses.c.department == status_data.department)
        ).values(
            status=status_data.status,
            remarks=status_data.remarks,
            cleared_by=cleared_by_user_id,
            updated_at=current_time
        )
        await database.execute(query)
        return {
            **status_data.dict(),
            "id": existing_status["id"],
            "cleared_by": cleared_by_user_id,
            "updated_at": current_time,
            "created_at": existing_status["created_at"]
        }
    else:
        # Create new status
        query = insert(clearance_statuses).values(
            student_id=status_data.student_id,
            department=status_data.department,
            status=status_data.status,
            remarks=status_data.remarks,
            cleared_by=cleared_by_user_id,
            updated_at=current_time,
            created_at=current_time
        )
        last_record_id = await database.execute(query)
        return {
            **status_data.dict(),
            "id": last_record_id,
            "cleared_by": cleared_by_user_id,
            "updated_at": current_time,
            "created_at": current_time
        }

async def update_clearance_status_by_staff(
    student_id: str, 
    department: ClearanceDepartment, 
    status_update: ClearanceStatusUpdate,
    staff_user_id: int
):
    """Updates clearance status by staff member."""
    query = update(clearance_statuses).where(
        (clearance_statuses.c.student_id == student_id) &
        (clearance_statuses.c.department == department)
    ).values(
        status=status_update.status,
        remarks=status_update.remarks,
        cleared_by=staff_user_id,
        updated_at=datetime.utcnow()
    )
    
    result = await database.execute(query)
    if result == 0:
        raise HTTPException(status_code=404, detail="Clearance status not found")
    
    # Return updated record
    query = select(clearance_statuses).where(
        (clearance_statuses.c.student_id == student_id) &
        (clearance_statuses.c.department == department)
    )
    return await database.fetch_one(query)

async def get_clearance_statuses_by_student_id(student_id: str):
    """Retrieves all clearance statuses for a given student ID."""
    query = select(clearance_statuses).where(clearance_statuses.c.student_id == student_id)
    return await database.fetch_all(query)

async def get_students_by_department_clearance(department: ClearanceDepartment):
    """Gets all students with their clearance status for a specific department."""
    query = select(
        students.c.student_id,
        students.c.name,
        students.c.department,
        clearance_statuses.c.status,
        clearance_statuses.c.remarks,
        clearance_statuses.c.updated_at
    ).select_from(
        students.join(
            clearance_statuses,
            students.c.student_id == clearance_statuses.c.student_id
        )
    ).where(clearance_statuses.c.department == department)
    
    return await database.fetch_all(query)

# --- CRUD operations for Devices ---

async def register_device(device_data: DeviceRegister):
    """Registers a new device or updates an existing one, generating an API key."""
    api_key = secrets.token_hex(16)
    current_time = datetime.utcnow()

    # Check if device already exists
    query = select(devices).where(devices.c.device_id == device_data.device_id)
    existing_device = await database.fetch_one(query)

    if existing_device:
        # Update existing device
        query = update(devices).where(devices.c.device_id == device_data.device_id).values(
            location=device_data.location,
            api_key=api_key,
            last_seen=current_time
        )
        await database.execute(query)
    else:
        # Create new device
        query = insert(devices).values(
            device_id=device_data.device_id,
            location=device_data.location,
            api_key=api_key,
            last_seen=current_time
        )
        await database.execute(query)

    return {
        "device_id": device_data.device_id,
        "location": device_data.location,
        "api_key": api_key
    }

async def update_device_last_seen(device_id: str):
    """Updates the 'last_seen' timestamp for a given device."""
    query = update(devices).where(devices.c.device_id == device_id).values(
        last_seen=datetime.utcnow()
    )
    await database.execute(query)

# --- CRUD operations for Device Logs ---

async def create_device_log(device_id: str, tag_id: str, action: str, user_type: str = "unknown"):
    """Creates a log entry for device activity."""
    query = device_logs.insert().values(
        device_id=device_id,
        tag_id=tag_id,
        user_type=user_type,
        timestamp=datetime.utcnow(),
        action=action
    )
    await database.execute(query)

# --- Dashboard and Statistics ---

async def get_clearance_statistics():
    """Gets overall clearance statistics for admin dashboard."""
    stats = {}
    
    for dept in ClearanceDepartment:
        # Count total students
        total_query = select(func.count(clearance_statuses.c.id)).where(
            clearance_statuses.c.department == dept
        )
        total = await database.fetch_val(total_query)
        
        # Count completed
        completed_query = select(func.count(clearance_statuses.c.id)).where(
            and_(
                clearance_statuses.c.department == dept,
                clearance_statuses.c.status == ClearanceStatusEnum.COMPLETED
            )
        )
        completed = await database.fetch_val(completed_query)
        
        stats[dept.value] = {
            "total_students": total or 0,
            "completed": completed or 0,
            "pending": (total or 0) - (completed or 0),
            "completion_rate": (completed / total * 100) if total > 0 else 0
        }
    
    return stats

async def get_students_with_clearance_summary():
    """Gets all students with their overall clearance status summary."""
    # This is a complex query that would benefit from a view in production
    query = """
    SELECT 
        s.student_id,
        s.name,
        s.department,
        COUNT(cs.id) as total_clearances,
        COUNT(CASE WHEN cs.status = 'COMPLETED' THEN 1 END) as completed_clearances,
        CASE 
            WHEN COUNT(CASE WHEN cs.status = 'COMPLETED' THEN 1 END) = COUNT(cs.id) 
            THEN 'COMPLETED' 
            ELSE 'PENDING' 
        END as overall_status
    FROM students s
    LEFT JOIN clearance_statuses cs ON s.student_id = cs.student_id
    GROUP BY s.student_id, s.name, s.department
    ORDER BY s.name
    """
    
    return await database.fetch_all(query)

async def update_student_tag_id(student_id: str, new_tag_id: str):
    """Updates the tag_id for a specific student."""
    # Check if student exists
    student_query = students.select().where(students.c.student_id == student_id)
    student_record = await database.fetch_one(student_query)
    if not student_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    # Check if the new_tag_id is already in use by another student
    if new_tag_id == student_record["tag_id"]:
        # No change needed, or raise an error if you want to prevent re-assigning the same tag
        # For now, we'll allow it, effectively a no-op if tag is same.
        pass # Or return student_record directly
    else:
        tag_query_student = students.select().where(and_(students.c.tag_id == new_tag_id, students.c.student_id != student_id))
        existing_student_tag = await database.fetch_one(tag_query_student)
        if existing_student_tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tag ID {new_tag_id} is already assigned to another student.")
        
        # Check if the new_tag_id is already in use by a staff/admin user
        tag_query_user = users.select().where(users.c.tag_id == new_tag_id)
        existing_user_tag = await database.fetch_one(tag_query_user)
        if existing_user_tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tag ID {new_tag_id} is already assigned to a staff/admin user.")

    # Update the tag_id
    update_query = students.update().where(students.c.student_id == student_id).values(tag_id=new_tag_id)
    await database.execute(update_query)
    
    # Fetch and return the updated student record
    updated_student_query = students.select().where(students.c.student_id == student_id)
    updated_student_record = await database.fetch_one(updated_student_query)
    return updated_student_record

async def update_user_tag_id(username: str, new_tag_id: str):
    """Updates the tag_id for a specific staff/admin user."""
    # Check if user exists
    user_query = users.select().where(users.c.username == username)
    user_record = await database.fetch_one(user_query)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if the new_tag_id is already in use by another staff/admin user
    if new_tag_id == user_record["tag_id"]:
        pass # No change needed
    else:
        tag_query_user = users.select().where(and_(users.c.tag_id == new_tag_id, users.c.username != username))
        existing_user_tag = await database.fetch_one(tag_query_user)
        if existing_user_tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tag ID {new_tag_id} is already assigned to another staff/admin user.")

        # Check if the new_tag_id is already in use by a student
        tag_query_student = students.select().where(students.c.tag_id == new_tag_id)
        existing_student_tag = await database.fetch_one(tag_query_student)
        if existing_student_tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tag ID {new_tag_id} is already assigned to a student.")

    # Update the tag_id
    update_query = users.update().where(users.c.username == username).values(tag_id=new_tag_id)
    await database.execute(update_query)
    
    # Fetch and return the updated user record (excluding password)
    updated_user_query = users.select().where(users.c.username == username)
    updated_user_record = await database.fetch_one(updated_user_query)
    return {key: value for key, value in updated_user_record.items() if key != "hashed_password"}

# --- Additional CRUD operations ---

def get_user_by_tag_id(db, tag_id: str):
    return db.query(User).filter(User.tag_id == tag_id, User.is_active == True).first()

def get_student_by_tag_id(db, tag_id: str):
    return db.query(Student).filter(Student.tag_id == tag_id, Student.is_active == True).first()

def is_tag_id_unique(db, tag_id: str) -> bool:
    user_exists = db.query(User).filter(User.tag_id == tag_id).first()
    student_exists = db.query(Student).filter(Student.tag_id == tag_id).first()
    return not user_exists and not student_exists

def update_student_tag_id(db, student_id: str, new_tag_id: str) -> Optional[Student]:
    if not is_tag_id_unique(db, new_tag_id):
        raise HTTPException(status_code=409, detail="Tag ID already in use by another user or student.")
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if student:
        student.tag_id = new_tag_id
        db.commit()
        db.refresh(student)
    return student

def update_user_tag_id(db, username: str, new_tag_id: str) -> Optional[User]:
    if not is_tag_id_unique(db, new_tag_id):
        raise HTTPException(status_code=409, detail="Tag ID already in use by another user or student.")
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.tag_id = new_tag_id
        db.commit()
        db.refresh(user)
    return user

# CRUD for Devices
def create_device(db, device: models.DeviceCreate) -> models.Device:
    api_key = secrets.token_urlsafe(32) # Generate a secure API key
    db_device = models.Device(**device.dict(), api_key=api_key)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def get_device_by_api_key(db, api_key: str) -> Optional[models.Device]:
    return db.query(models.Device).filter(models.Device.api_key == api_key, models.Device.is_active == True).first()

def get_devices(db, skip: int = 0, limit: int = 100) -> List[models.Device]:
    return db.query(models.Device).offset(skip).limit(limit).all()

def get_device(db, device_id: int) -> Optional[models.Device]:
    return db.query(models.Device).filter(models.Device.id == device_id).first()

# CRUD for PendingTagLink
def create_pending_tag_link(db, device_api_key: str, target_user_type: TargetUserType, target_identifier: str, initiated_by_user_id: int, expires_in_minutes: int = 5) -> models.PendingTagLink:
    # Check if device exists and is active
    device = get_device_by_api_key(db, device_api_key)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with API key {device_api_key} not found or inactive.")

    # Check if target user/student exists
    if target_user_type == TargetUserType.STUDENT:
        student = get_student_by_student_id(db, target_identifier)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student with ID {target_identifier} not found.")
        if student.tag_id:
            raise HTTPException(status_code=409, detail=f"Student {target_identifier} already has a tag linked.")
    elif target_user_type == TargetUserType.STAFF_ADMIN:
        user = get_user_by_tag_id(db, target_identifier) # Assuming get_user fetches by username
        if not user:
            raise HTTPException(status_code=404, detail=f"User with username {target_identifier} not found.")
        if user.tag_id:
            raise HTTPException(status_code=409, detail=f"User {target_identifier} already has a tag linked.")
    else:
        raise HTTPException(status_code=400, detail="Invalid target user type.")

    # Check for existing pending link for this device to prevent conflicts
    existing_pending_link = db.query(models.PendingTagLink).filter(
        models.PendingTagLink.device_api_key == device_api_key,
        models.PendingTagLink.expires_at > datetime.utcnow()
    ).first()
    if existing_pending_link:
        raise HTTPException(status_code=409, detail=f"Device {device.name} is already waiting for a tag scan for another user. Please wait or use a different device.")

    expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    db_pending_link = models.PendingTagLink(
        device_api_key=device_api_key,
        target_user_type=target_user_type,
        target_identifier=target_identifier,
        initiated_by_user_id=initiated_by_user_id,
        expires_at=expires_at
    )
    db.add(db_pending_link)
    db.commit()
    db.refresh(db_pending_link)
    return db_pending_link

def get_pending_tag_link_by_device_api_key(db, device_api_key: str) -> Optional[models.PendingTagLink]:
    return db.query(models.PendingTagLink).filter(
        models.PendingTagLink.device_api_key == device_api_key,
        models.PendingTagLink.expires_at > datetime.utcnow()
    ).order_by(models.PendingTagLink.created_at.desc()).first()

def delete_pending_tag_link(db, pending_link_id: int):
    db_pending_link = db.query(models.PendingTagLink).filter(models.PendingTagLink.id == pending_link_id).first()
    if db_pending_link:
        db.delete(db_pending_link)
        db.commit()
    return db_pending_link