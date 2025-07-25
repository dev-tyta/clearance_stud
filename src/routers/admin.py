from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, SQLModel
from typing import List, Optional, Dict

from src.database import get_session
from src.auth import get_current_active_user, get_api_key
from src.models import (
    User, UserCreate, UserRead, UserUpdate, Role,
    Student, StudentCreate, StudentReadWithClearance, StudentUpdate, StudentRead,
    TagLink, RFIDTagRead, Device, DeviceCreate, DeviceRead, TagScan
)
from src.crud import users as user_crud
from src.crud import students as student_crud
from src.crud import tag_linking as tag_crud
from src.crud import devices as device_crud

# --- New State Management for Secure Admin Scanning ---

# Maps a device's API key to the admin user ID who activated it.
# This "activates" a scanner for a specific admin.
activated_scanners: Dict[str, int] = {} 

# Stores the last tag scanned by a device, keyed by the admin ID who was waiting.
admin_scanned_tags: Dict[int, str] = {}


# Define the main administrative router
router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(get_current_active_user(required_roles=[Role.ADMIN, Role.STAFF]))],
)

# --- New Secure Scanning Workflow ---

class ActivationRequest(SQLModel):
    device_id: int

@router.post("/scanners/activate", status_code=status.HTTP_204_NO_CONTENT)
def activate_admin_scanner(
    activation: ActivationRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user(required_roles=[Role.ADMIN, Role.STAFF]))
):
    """
    STEP 1 (Browser): Admin clicks "Scan Card" in the UI.
    The browser calls this endpoint to 'arm' their designated desk scanner.
    """
    device = device_crud.get_device_by_id(db, device_id=activation.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    
    # Map the device's API key to the currently logged-in admin's ID.
    activated_scanners[device.api_key] = current_user.id
    return


@router.post("/scanners/scan", status_code=status.HTTP_204_NO_CONTENT)
def receive_scan_from_activated_device(
    scan_data: TagScan,
    api_key: str = Depends(get_api_key) # Device authenticates with its API Key
):
    """
    STEP 2 (Device): The ESP32 device sends the scanned tag to this endpoint.
    This endpoint is protected by the device's API Key.
    """
    # Check if this device was activated by an admin.
    admin_id = activated_scanners.pop(api_key, None)
    if admin_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This scanner has not been activated for a scan.")

    # Store the scanned tag against the admin who was waiting for it.
    admin_scanned_tags[admin_id] = scan_data.tag_id
    return

@router.get("/scanners/retrieve", response_model=TagScan)
def retrieve_scanned_tag_for_ui(
    current_user: User = Depends(get_current_active_user(required_roles=[Role.ADMIN, Role.STAFF]))
):
    """
    STEP 3 (Browser): The browser polls this endpoint to get the tag ID
    that the device reported in STEP 2.
    """
    tag_id = admin_scanned_tags.pop(current_user.id, None)
    if not tag_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tag has been scanned by the activated device yet.")
    return TagScan(tag_id=tag_id)


# --- All other administrative endpoints remain the same ---
# ... (Student Management, User Management, etc.) ...
@router.post("/students/", response_model=StudentReadWithClearance, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate, db: Session = Depends(get_session)):
    """(Admin & Staff) Creates a new student and initializes their clearance status."""
    db_student = student_crud.get_student_by_matric_no(db, matric_no=student.matric_no)
    if db_student:
        raise HTTPException(status_code=400, detail="Matriculation number already registered")
    return student_crud.create_student(db=db, student=student)

@router.get("/students/", response_model=List[StudentReadWithClearance])
def read_all_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    """(Admin & Staff) Retrieves a list of all student records."""
    return student_crud.get_all_students(db, skip=skip, limit=limit)

@router.get("/students/lookup", response_model=StudentReadWithClearance)
def lookup_student(
    matric_no: Optional[str] = Query(None, description="Matriculation number of the student."),
    tag_id: Optional[str] = Query(None, description="RFID tag ID linked to the student."),
    db: Session = Depends(get_session)
):
    """(Admin & Staff) Looks up a single student by Matric Number OR Tag ID."""
    if not matric_no and not tag_id:
        raise HTTPException(status_code=400, detail="A matric_no or tag_id must be provided.")
    if matric_no and tag_id:
        raise HTTPException(status_code=400, detail="Provide either matric_no or tag_id, not both.")

    db_student = None
    if matric_no:
        db_student = student_crud.get_student_by_matric_no(db, matric_no=matric_no)
    elif tag_id:
        db_student = student_crud.get_student_by_tag_id(db, tag_id=tag_id)
    
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found with the provided identifier.")
    return db_student


@router.get("/students/{student_id}", response_model=StudentReadWithClearance)
def read_single_student(student_id: int, db: Session = Depends(get_session)):
    """(Admin & Staff) Retrieves a single student's complete record by their internal ID."""
    db_student = student_crud.get_student_by_id(db, student_id=student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    return db_student

@router.put("/students/{student_id}", response_model=StudentReadWithClearance)
def update_student_details(student_id: int, student: StudentUpdate, db: Session = Depends(get_session)):
    """(Admin & Staff) Updates a student's information."""
    updated_student = student_crud.update_student(db, student_id=student_id, student_update=student)
    if not updated_student:
        raise HTTPException(status_code=404, detail="Student not found")
    return updated_student

# --- Tag Management (Admin + Staff) ---

@router.post("/tags/link", response_model=RFIDTagRead)
def link_rfid_tag(link_data: TagLink, db: Session = Depends(get_session)):
    """(Admin & Staff) Links an RFID tag to a student or user."""
    new_tag = tag_crud.link_tag(db, link_data)
    if not new_tag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not link tag. The tag may already be in use, or the user/student already has a tag."
        )
    return new_tag

@router.delete("/tags/{tag_id}/unlink", response_model=RFIDTagRead)
def unlink_rfid_tag(tag_id: str, db: Session = Depends(get_session)):
    """(Admin & Staff) Unlinks an RFID tag, making it available again."""
    deleted_tag = tag_crud.unlink_tag(db, tag_id)
    if not deleted_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFID Tag not found."
        )
    return deleted_tag


# --- Super Admin Only Functions ---

def require_super_admin(current_user: User = Depends(get_current_active_user())):
    """Dependency to ensure a user has the ADMIN role."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires Super Admin privileges."
        )

@router.post(
    "/users/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_active_user(required_roles=[Role.ADMIN]))]
)
def create_user_as_admin(user: UserCreate, db: Session = Depends(get_session)):
    """(Super Admin Only) Creates a new user (admin or staff)."""
    if user_crud.get_user_by_username(db, username=user.username):
        raise HTTPException(status_code=400, detail="Username already registered.")
    if user_crud.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    return user_crud.create_user(db=db, user=user)

@router.get("/users/", response_model=List[UserRead], dependencies=[Depends(require_super_admin)])
def read_all_users(db: Session = Depends(get_session)):
    """(Super Admin Only) Retrieves a list of all users."""
    return user_crud.get_all_users(db)

@router.get("/users/lookup", response_model=UserRead, dependencies=[Depends(require_super_admin)])
def lookup_user(
    username: Optional[str] = Query(None, description="Username of the user."),
    tag_id: Optional[str] = Query(None, description="RFID tag ID linked to the user."),
    db: Session = Depends(get_session)
):
    """(Super Admin Only) Looks up a single user by Username OR Tag ID."""
    if not username and not tag_id:
        raise HTTPException(status_code=400, detail="A username or tag_id must be provided.")
    if username and tag_id:
        raise HTTPException(status_code=400, detail="Provide either username or tag_id, not both.")

    db_user = None
    if username:
        db_user = user_crud.get_user_by_username(db, username=username)
    elif tag_id:
        db_user = user_crud.get_user_by_tag_id(db, tag_id=tag_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found with the provided identifier.")
    return db_user

@router.put("/users/{user_id}", response_model=UserRead, dependencies=[Depends(require_super_admin)])
def update_user_details(user_id: int, user: UserUpdate, db: Session = Depends(get_session)):
    """(Super Admin Only) Updates a user's details (e.g., role)."""
    updated_user = user_crud.update_user(db, user_id=user_id, user_update=user)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.delete("/users/{user_id}", response_model=UserRead, dependencies=[Depends(require_super_admin)])
def delete_user_account(user_id: int, db: Session = Depends(get_session), current_user: User = Depends(get_current_active_user())):
    """(Super Admin Only) Deletes a user account."""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    deleted_user = user_crud.delete_user(db, user_id=user_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted_user

@router.delete("/students/{student_id}", response_model=StudentRead, dependencies=[Depends(require_super_admin)])
def delete_student_record(student_id: int, db: Session = Depends(get_session)):
    """(Super Admin Only) Deletes a student record and all associated data."""
    deleted_student = student_crud.delete_student(db, student_id=student_id)
    if not deleted_student:
        raise HTTPException(status_code=404, detail="Student not found")
    return deleted_student

@router.post("/devices/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_super_admin)])
def create_device(device: DeviceCreate, db: Session = Depends(get_session)):
    """(Super Admin Only) Registers a new RFID hardware device."""
    db_device = device_crud.get_device_by_location(db, location=device.location)
    if db_device:
        raise HTTPException(status_code=400, detail=f"A device at location '{device.location}' already exists.")
    return device_crud.create_device(db=db, device=device)

@router.get("/devices/", response_model=List[DeviceRead], dependencies=[Depends(require_super_admin)])
def read_all_devices(db: Session = Depends(get_session)):
    """(Super Admin Only) Retrieves a list of all registered devices."""
    return device_crud.get_all_devices(db)

@router.delete("/devices/{device_id}", response_model=DeviceRead, dependencies=[Depends(require_super_admin)])
def delete_device_registration(device_id: int, db: Session = Depends(get_session)):
    """(Super Admin Only) De-authorizes a hardware device."""
    deleted_device = device_crud.delete_device(db, device_id=device_id)
    if not deleted_device:
        raise HTTPException(status_code=404, detail="Device not found")
    return deleted_device
