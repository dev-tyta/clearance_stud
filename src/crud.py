# Import database instance and tables from database.py
from src.database import database, students, clearance_statuses, device_logs, devices
from src.models import StudentCreate, ClearanceStatusCreate, TagScan, DeviceRegister # Import Pydantic models
# Import necessary SQLAlchemy components for building queries
from sqlalchemy import select, insert, update
from datetime import datetime
import secrets # For generating API keys
from fastapi import HTTPException # Import HTTPException to raise errors

# --- CRUD operations for Students ---

async def create_student(student: StudentCreate):
    """Creates a new student record in the database using 'databases'."""
    # Build an insert query using SQLAlchemy
    query = students.insert().values(
        student_id=student.student_id,
        name=student.name,
        department=student.department,
        tag_id=student.tag_id
    )
    # Execute the query asynchronously using 'databases'
    last_record_id = await database.execute(query)
    # Return the created student data including the generated ID
    return {**student.dict(), "id": last_record_id}

async def get_all_students():
    """Retrieves all student records from the database using 'databases'."""
    # Build a select query using SQLAlchemy
    query = students.select()
    # Execute the query and fetch all results asynchronously
    return await database.fetch_all(query)

async def get_student_by_student_id(student_id: str):
    """Retrieves a student record by their student ID using 'databases'."""
    # Build a select query with a where clause
    query = students.select().where(students.c.student_id == student_id)
    # Execute the query and fetch one result asynchronously
    return await database.fetch_one(query)

async def get_student_by_tag_id(tag_id: str):
    """Retrieves a student record by their tag ID using 'databases'."""
    # Build a select query with a where clause
    query = students.select().where(students.c.tag_id == tag_id)
    # Execute the query and fetch one result asynchronously
    return await database.fetch_one(query)

# --- CRUD operations for Clearance Statuses ---

async def create_or_update_clearance_status(status_data: ClearanceStatusCreate):
    """Creates a new clearance status or updates an existing one using 'databases'."""
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
            updated_at=current_time
        )
        await database.execute(query)
        # Return the updated record including the existing ID and new timestamp
        return {
            **status_data.dict(),
            "id": existing_status["id"],
            "updated_at": current_time
        }
    else:
        # Create new status
        query = insert(clearance_statuses).values(
            student_id=status_data.student_id,
            department=status_data.department,
            status=status_data.status,
            remarks=status_data.remarks,
            updated_at=current_time
        )
        last_record_id = await database.execute(query)
        # Return the newly created record including the new ID and timestamp
        return {
            **status_data.dict(),
            "id": last_record_id,
            "updated_at": current_time
        }


async def get_clearance_statuses_by_student_id(student_id: str):
    """Retrieves all clearance statuses for a given student ID using 'databases'."""
    query = select(clearance_statuses).where(clearance_statuses.c.student_id == student_id)
    return await database.fetch_all(query)

# --- CRUD operations for Devices ---

async def register_device(device_data: DeviceRegister):
    """Registers a new device or updates an existing one, generating an API key using 'databases'."""
    api_key = secrets.token_hex(16) # Generate a unique API key
    current_time = datetime.utcnow()

    # Check if device already exists
    query = select(devices).where(devices.c.device_id == device_data.device_id)
    existing_device = await database.fetch_one(query)

    if existing_device:
        # Update existing device
        query = update(devices).where(devices.c.device_id == device_data.device_id).values(
            location=device_data.location,
            api_key=api_key, # Assign a new API key on re-registration
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

    # Return the device details including the generated API key
    # We need to fetch the newly created/updated device to get the assigned API key
    query = select(devices).where(devices.c.device_id == device_data.device_id)
    updated_device = await database.fetch_one(query)
    return {"device_id": updated_device["device_id"], "location": updated_device["location"], "api_key": updated_device["api_key"]}


async def update_device_last_seen(device_id: str):
    """Updates the 'last_seen' timestamp for a given device using 'databases'."""
    query = update(devices).where(devices.c.device_id == device_id).values(last_seen=datetime.utcnow())
    await database.execute(query)

# --- CRUD operations for Device Logs ---

async def create_device_log(device_id: str, tag_id: str, action: str):
    """Creates a log entry for device activity using 'databases'."""
    query = device_logs.insert().values(
        device_id=device_id,
        tag_id=tag_id,
        timestamp=datetime.utcnow(),
        action=action
    )
    await database.execute(query)
