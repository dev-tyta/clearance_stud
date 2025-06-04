from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, models, schemas # schemas might be your models.py or a separate schemas.py
from ..database import get_db
from ..auth import get_current_active_admin_user, get_current_user_from_token, oauth2_scheme, get_verified_device

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_admin_user)] # Secure all admin routes
)

# Device Management Endpoints
@router.post("/devices/", response_model=models.DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_new_device(device: models.DeviceCreate, db: Session = Depends(get_db)):
    """
    Admin-only endpoint to register a new ESP32/RFID reader device.
    Generates an API key for the device.
    """
    return crud.create_device(db=db, device=device)

@router.get("/devices/", response_model=List[models.DeviceResponse])
def list_all_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Admin-only endpoint to list all registered devices.
    """
    devices = crud.get_devices(db, skip=skip, limit=limit)
    return devices

@router.get("/devices/{device_id}", response_model=models.DeviceResponse)
def get_device_details(device_id: int, db: Session = Depends(get_db)):
    """
    Admin-only endpoint to get details of a specific device.
    """
    db_device = crud.get_device(db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device

# Tag Linking Preparation Endpoint
@router.post("/prepare-device-tag-link", status_code=status.HTTP_202_ACCEPTED)
async def prepare_device_for_tag_linking(
    request: models.PrepareTagLinkRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_active_admin_user)
):
    """
    Admin prepares a registered device to link the next scanned tag to a specific user/student.
    The device will then scan a tag and submit it via /api/devices/submit-scanned-tag.
    """
    try:
        pending_link = crud.create_pending_tag_link(
            db=db,
            device_api_key=request.device_api_key,
            target_user_type=request.target_user_type,
            target_identifier=request.target_identifier,
            initiated_by_user_id=current_admin.id, # Assuming User model has 'id'
            expires_in_minutes=5 # Or make this configurable
        )
        # Fetch device name for a more informative message
        device = crud.get_device_by_api_key(db, request.device_api_key)
        device_name = device.name if device else request.device_api_key

        return {
            "message": f"Device '{device_name}' is now ready to scan a tag for {request.target_user_type.value} '{request.target_identifier}'. Tag scan must occur within 5 minutes.",
            "pending_link_id": pending_link.id
        }
    except HTTPException as e:
        raise e # Re-raise HTTPExceptions from CRUD
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")