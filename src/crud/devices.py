"""
CRUD operations for Devices and Device Logs.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status

from src import models

def get_device_by_id_str(db: Session, device_id: str) -> models.Device | None:
    """Fetches a device by its public device_id string."""
    return db.query(models.Device).filter(models.Device.device_id == device_id).first()

def get_device_by_api_key(db: Session, api_key: str) -> models.Device | None:
    """Fetches a device by its unique API key for authentication."""
    return db.query(models.Device).filter(models.Device.api_key == api_key).first()

def update_device_last_seen(db: Session, device_id: int):
    """Updates the last_seen timestamp for a device."""
    db.query(models.Device).filter(models.Device.id == device_id).update({"last_seen": datetime.utcnow()})
    db.commit()

def create_device_log(db: Session, log_data: dict):
    """Creates a new log entry for a device action."""
    new_log = models.DeviceLog(**log_data)
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log

def delete_device(db: Session, device_id_str: str) -> models.Device:
    """
    Deletes a device and all of its associated records (logs, pending links).
    """
    device_to_delete = get_device_by_id_str(db, device_id_str)
    if not device_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{device_id_str}' not found."
        )
    
    device_pk_id = device_to_delete.id

    # Delete all dependent records first to maintain foreign key integrity
    db.query(models.DeviceLog).filter(models.DeviceLog.device_fk_id == device_pk_id).delete(synchronize_session=False)
    db.query(models.PendingTagLink).filter(models.PendingTagLink.device_id_fk == device_pk_id).delete(synchronize_session=False)

    # Now delete the device itself
    db.delete(device_to_delete)
    db.commit()

    return device_to_delete
