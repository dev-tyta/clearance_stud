from sqlmodel import Session, select
import secrets
from typing import List, Optional

from src.models import Device, DeviceCreate, Department

def create_device(db: Session, device: DeviceCreate) -> Optional[Device]:
    """
    Creates a new device for a department.
    Generates a unique API key for authentication.
    Returns None if a device with the same name already exists.
    """
    # Check for existing device with the same name to prevent duplicates
    existing_device = db.exec(select(Device).where(Device.device_name == device.device_name)).first()
    if existing_device:
        return None

    # Generate a secure, URL-safe API key
    api_key = secrets.token_urlsafe(32)
    
    db_device = Device(
        device_name=device.device_name,
        department=device.department,
        api_key=api_key,
        is_active=True
    )
    
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def get_device_by_api_key(db: Session, api_key: str) -> Optional[Device]:
    """Retrieves an active device by its API key."""
    statement = select(Device).where(Device.api_key == api_key, Device.is_active == True)
    return db.exec(statement).first()

def get_device_by_name(db: Session, device_name: str) -> Optional[Device]:
    """Retrieves a device by its unique name."""
    return db.exec(select(Device).where(Device.device_name == device_name)).first()

def get_all_devices(db: Session, skip: int = 0, limit: int = 100) -> List[Device]:
    """Retrieves a list of all devices."""
    return db.exec(select(Device).offset(skip).limit(limit)).all()

def update_device(db: Session, device_id: int, device_update: dict) -> Optional[Device]:
    """
    Updates a device's mutable properties (e.g., name, active status).
    The API key is immutable and cannot be changed here.
    """
    db_device = db.get(Device, device_id)
    if not db_device:
        return None
    
    # Exclude API key from updates for security
    device_update.pop("api_key", None)

    for key, value in device_update.items():
        setattr(db_device, key, value)
        
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def delete_device(db: Session, device_id: int) -> Optional[Device]:
    """Deletes a device from the database."""
    db_device = db.get(Device, device_id)
    if not db_device:
        return None
    
    db.delete(db_device)
    db.commit()
    return db_device
