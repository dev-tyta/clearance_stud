"""
Admin-only endpoints for managing system-wide operations like tag linking
and deleting core resources like users and devices.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src import crud, models
from src.auth import get_current_active_admin_user_from_token, get_current_active_user
from src.database import get_db

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_active_admin_user_from_token)]
)

@router.post("/prepare-tag-link", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def prepare_device_for_tag_linking(
    request: models.PrepareTagLinkRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Initiates a request to link a tag. This creates a temporary,
    expiring 'PendingTagLink' record for a device.
    """
    device = await run_in_threadpool(crud.get_device_by_id_str, db, request.device_identifier)
    if not device or not device.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found or is inactive.")
    
    if request.target_user_type == models.TargetUserType.STUDENT:
        target = await run_in_threadpool(crud.get_student_by_student_id, db, request.target_identifier)
    else:
        target = await run_in_threadpool(crud.get_user_by_username, db, request.target_identifier)
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{request.target_user_type.value} '{request.target_identifier}' not found."
        )

    expiry_time = datetime.utcnow() + timedelta(minutes=2)
    await run_in_threadpool(
        crud.create_pending_tag_link, db, request, current_user.id, expiry_time
    )
    return {
        "message": "Device is ready to link tag.",
        "device_id": device.device_id,
        "target": request.target_identifier,
        "expires_at": expiry_time.isoformat()
    }

@router.delete("/users/{username}", status_code=status.HTTP_200_OK, response_model=dict)
async def delete_user_endpoint(
    username: str,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_active_admin_user_from_token)
):
    """
    Admin: Permanently deletes a user (staff or other admin).
    """
    try:
        deleted_user = await run_in_threadpool(crud.delete_user, db, username, current_admin)
        return {"message": "User deleted successfully", "username": deleted_user.username}
    except HTTPException as e:
        raise e

@router.delete("/devices/{device_id_str}", status_code=status.HTTP_200_OK, response_model=dict)
async def delete_device_endpoint(
    device_id_str: str,
    db: Session = Depends(get_db)
):
    """
    Admin: Permanently deletes a registered RFID device and all its logs.
    """
    try:
        deleted_device = await run_in_threadpool(crud.delete_device, db, device_id_str)
        return {"message": "Device deleted successfully", "device_id": deleted_device.device_id}
    except HTTPException as e:
        raise e
