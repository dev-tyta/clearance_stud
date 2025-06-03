from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List # Import List for type hinting
from src.database import connect_db, disconnect_db, database # Also import database instance if needed directly in main
from src.models import (
    StudentCreate, Student, ClearanceStatusCreate,
    ClearanceStatus, ClearanceDetail, DeviceRegister,
    DeviceResponse, TagScan
) # Pydantic models
from src import crud # Database operations (now uses databases)
from src.auth import verify_api_key # API key verification dependency (now uses databases)

# FastAPI app instance
app = FastAPI(title="Undergraduate Clearance System API", version="1.0.0")

# Enable CORS (Cross-Origin Resource Sharing)
# This allows your frontend (running on a different origin) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WARNING: Use specific origins in production (e.g., ["http://localhost:3000", "https://your-frontend-domain.com"])
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# --- Database Connection Lifecycle ---

# Connect to the database when the application starts up
@app.on_event("startup")
async def startup_event():
    await connect_db()

# Disconnect from the database when the application shuts down
@app.on_event("shutdown")
async def shutdown_event():
    await disconnect_db()


# --- Routes for ESP32 Devices ---

@app.post("/api/devices/register", response_model=DeviceResponse, summary="Register or re-register an ESP32 device")
async def register_device(device: DeviceRegister):
    """
    Registers a new ESP32 device or updates an existing one using 'databases'.
    Returns a unique API key for the device to use for subsequent requests.
    """
    # Call the crud function, which now uses 'databases'
    return await crud.register_device(device)

@app.post("/api/scan", summary="Receive tag scan data from an ESP32 device and return clearance details")
async def scan_tag(scan_data: TagScan):
    """
    Receives a tag ID from an ESP32 device, verifies the device's API key
    using 'databases', logs the scan event, retrieves the student's
    clearance details based on the tag ID, and returns the details to the device.
    """
    # Verify API key using the dependency - this will raise HTTPException if invalid
    # The verify_api_key function now uses 'databases'
    device = await verify_api_key(scan_data.api_key)

    # Update device last seen timestamp using the crud function (which uses databases)
    await crud.update_device_last_seen(scan_data.device_id)

    # Log the scan event using the crud function (which uses databases)
    await crud.create_device_log(scan_data.device_id, scan_data.tag_id, "scan")

    # Get student information by tag ID using the crud function (which uses databases)
    student = await crud.get_student_by_tag_id(scan_data.tag_id)

    if not student:
        # Return a specific message to the device if student is not found
        # The ESP32 firmware should handle this 404 response
        raise HTTPException(status_code=404, detail="Student not found for this tag")

    # Get clearance statuses for the student using the crud function (which uses databases)
    statuses = await crud.get_clearance_statuses_by_student_id(student["student_id"])

    # Format clearance items and determine overall status
    clearance_items = []
    overall_status = True

    for status_item in statuses:
        clearance_items.append({
            "department": status_item["department"],
            "status": status_item["status"],
            "remarks": status_item["remarks"],
            "updated_at": status_item["updated_at"].isoformat() # Format datetime to ISO string
        })
        if not status_item["status"]:
            overall_status = False

    # Return the formatted clearance details
    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "department": student["department"],
        "clearance_items": clearance_items,
        "overall_status": overall_status
    }

# --- Student Management Routes (Likely for Frontend/Admin Use) ---

@app.post("/api/students/", response_model=Student, status_code=status.HTTP_201_CREATED, summary="Create a new student")
async def create_student(student: StudentCreate):
    """Creates a new student record using 'databases'."""
    # Check if student ID already exists using the crud function (which uses databases)
    existing_student_by_id = await crud.get_student_by_student_id(student.student_id)
    if existing_student_by_id:
        raise HTTPException(status_code=400, detail="Student ID already registered")

    # Check if tag ID already exists using the crud function (which uses databases)
    existing_student_by_tag = await crud.get_student_by_tag_id(student.tag_id)
    if existing_student_by_tag:
        raise HTTPException(status_code=400, detail="Tag ID already assigned to another student")

    # Create the student using the crud function (which uses databases)
    return await crud.create_student(student)

@app.get("/api/students/", response_model=List[Student], summary="Get all students")
async def get_students():
    """Retrieves a list of all students using 'databases'."""
    # Get all students using the crud function (which uses databases)
    return await crud.get_all_students()

@app.get("/api/students/{student_id}", response_model=ClearanceDetail, summary="Get clearance details for a specific student")
async def get_student_clearance(student_id: str):
    """
    Retrieves the full clearance details for a student based on their student ID
    using 'databases'. This endpoint is likely used by the frontend/admin interface.
    """
    # Get student info using the crud function (which uses databases)
    student = await crud.get_student_by_student_id(student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get clearance status using the crud function (which uses databases)
    statuses = await crud.get_clearance_statuses_by_student_id(student_id)

    # Format clearance items and determine overall status
    clearance_items = []
    overall_status = True

    for status_item in statuses:
        clearance_items.append({
            "department": status_item["department"],
            "status": status_item["status"],
            "remarks": status_item["remarks"],
            "updated_at": status_item["updated_at"].isoformat() # Format datetime to ISO string
        })
        if not status_item["status"]:
            overall_status = False

    # Return the formatted clearance details
    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "department": student["department"],
        "clearance_items": clearance_items,
        "overall_status": overall_status
    }

# --- Clearance Management Routes (Likely for Frontend/Admin Use) ---

@app.post("/api/clearance/", response_model=ClearanceStatus, summary="Create or update a student's clearance status for a department")
async def update_clearance_status(status_data: ClearanceStatusCreate):
    """
    Creates a new clearance status entry for a student and department,
    or updates an existing one using 'databases'.
    """
    # Check if student exists using the crud function (which uses databases)
    student = await crud.get_student_by_student_id(status_data.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Create or update the clearance status using the crud function (which uses databases)
    return await crud.create_or_update_clearance_status(status_data)


# --- Root Endpoint (Optional) ---
@app.get("/", summary="Root endpoint")
async def read_root():
    """Basic root endpoint to confirm the API is running."""
    return {"message": "Undergraduate Clearance System API is running"}


# --- Run the FastAPI app ---
if __name__ == "__main__":
    # Use uvicorn to run the FastAPI application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
