from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySessionType
from typing import List, Optional, Dict

from src import crud, models # crud functions are now sync ORM
from src.database import get_db
from src.auth import (
    get_current_active_admin_user_from_token, # Returns ORM User model (Token-based)
)
from fastapi.concurrency import run_in_threadpool 

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_admin_user_from_token)]
)

# --- Device Management Endpoints (Synchronous ORM) ---
@router.post("/devices/", response_model=models.DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_new_device_admin( # Endpoint is synchronous
    device_data: models.DeviceCreateAdmin,
    db: SQLAlchemySessionType = Depends(get_db),
    current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token) # For logging who did it
):
    """
    Admin registers a new ESP32/RFID reader device. Uses ORM.
    """
    print(f"Admin '{current_admin_orm.username}' creating device: {device_data.name}")
    try:
        created_device_orm = crud.create_device(db=db, device_data=device_data)
    except HTTPException as e:
        raise e
    return created_device_orm # Pydantic converts from ORM model

@router.get("/devices/", response_model=List[models.DeviceResponse])
def list_all_devices_admin( # Endpoint is synchronous
    skip: int = 0,
    limit: int = 100,
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    Admin lists all registered devices. Uses ORM.
    """
    devices_orm_list = crud.get_all_devices(db, skip=skip, limit=limit)
    return devices_orm_list

@router.get("/devices/{device_pk_id}", response_model=models.DeviceResponse)
def get_device_details_admin( # Endpoint is synchronous
    device_pk_id: int,
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    Admin gets details of a specific device by its Primary Key. Uses ORM.
    """
    # crud.get_device_by_pk is now sync ORM
    db_device_orm = crud.get_device_by_pk(db, device_pk=device_pk_id)
    if db_device_orm is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device_orm

# --- Tag Linking Preparation Endpoint (Synchronous ORM) ---
@router.post("/prepare-device-tag-link", status_code=status.HTTP_202_ACCEPTED, response_model=Dict)
def prepare_device_for_tag_linking_admin( # Endpoint is synchronous
    request_payload: models.PrepareTagLinkRequest,
    db: SQLAlchemySessionType = Depends(get_db),
    current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token)
):
    """
    Admin prepares a device for tag linking. Uses synchronous ORM.
    """
    device_identifier_val = request_payload.device_identifier
    device_orm_instance: Optional[models.Device] = None

    try: 
        device_pk = int(device_identifier_val)
        device_orm_instance = crud.get_device_by_pk(db, device_pk)
    except ValueError: # If not an int, assume it's the hardware string ID
        device_orm_instance = crud.get_device_by_hardware_id(db, device_identifier_val)

    if not device_orm_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device with identifier '{device_identifier_val}' not found.")
    if not device_orm_instance.is_active: # Check if device is active
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Device '{device_orm_instance.name or device_orm_instance.device_id}' is not active.")

    device_pk_for_link = device_orm_instance.id
    admin_user_pk = current_admin_orm.id # User's primary key

    try:
        pending_link_orm = crud.create_pending_tag_link(
            db=db,
            device_pk=device_pk_for_link,
            target_user_type=request_payload.target_user_type,
            target_identifier=request_payload.target_identifier,
            initiated_by_user_pk=admin_user_pk, # Pass admin's PK
            expires_in_minutes=5
        )
        
        device_display_name = device_orm_instance.name or device_orm_instance.device_id or f"PK:{device_pk_for_link}"
        return {
            "message": f"Device '{device_display_name}' is now ready to scan a tag for {request_payload.target_user_type.value} '{request_payload.target_identifier}'. Tag scan must occur within 5 minutes.",
            "pending_link_id": pending_link_orm.id,
            "expires_at": pending_link_orm.expires_at.isoformat()
        }
    except HTTPException as e: # Catch known exceptions from CRUD (e.g., 409 if device busy)
        raise e
    except Exception as e:
        print(f"Unexpected error in prepare_device_for_tag_linking_admin: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

