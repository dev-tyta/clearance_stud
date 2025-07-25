from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from src.database import get_session
from src.auth import get_current_active_user
from src.models import Role, Device, DeviceCreate, DeviceRead
from src.crud import devices as device_crud

# Define the router with admin-only access
router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
    dependencies=[Depends(get_current_active_user(required_roles=[Role.ADMIN]))],
)

@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate, 
    db: Session = Depends(get_session)
):
    """
    Admin endpoint to register a new RFID hardware device.
    
    This generates a unique API key that the device must use to authenticate.
    A device's location must be unique.
    """
    # Check if a device with the same location already exists
    db_device = device_crud.get_device_by_location(db, location=device.location)
    if db_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A device at location '{device.location}' already exists."
        )
    
    # Create the new device and its API key
    return device_crud.create_device(db=db, device=device)


@router.get("/", response_model=List[DeviceRead])
def read_all_devices(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_session)
):
    """
    Admin endpoint to retrieve a list of all registered hardware devices.
    """
    return device_crud.get_all_devices(db, skip=skip, limit=limit)


@router.delete("/{device_id}", response_model=DeviceRead)
def delete_device(
    device_id: int, 
    db: Session = Depends(get_session)
):
    """
    Admin endpoint to delete/de-authorize a hardware device.
    
    This will render the device's API key invalid.
    """
    db_device = device_crud.delete_device(db, device_id=device_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )
    return db_device
