"""
Router for device interactions, specifically for submitting a scanned tag.
This endpoint is intended to be called by the physical RFID reader device.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import Union

from src import crud, models
from src.database import get_db
from src.utils import format_student_clearance_details

async def get_authenticated_device(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> models.Device:
    """Dependency to authenticate a device by its API key."""
    device = await run_in_threadpool(crud.get_device_by_api_key, db, x_api_key)
    if not device or not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key or Inactive Device",
        )
    return device

router = APIRouter(
    prefix="/api/devices",
    tags=["Devices"],
    dependencies=[Depends(get_authenticated_device)]
)

@router.post(
    "/submit-tag",
    response_model=Union[models.ClearanceDetail, models.UserResponse, dict],
    summary="Endpoint for RFID devices to submit a scanned tag ID."
)
async def device_submit_scanned_tag(
    scanned_tag: models.ScannedTagSubmit,
    device: models.Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db)
):
    """
    Handles a tag submission from an authenticated RFID device.
    It can either link a tag if a pending link exists or fetch user details.
    """
    tag_id = scanned_tag.scanned_tag_id
    pending_link = await run_in_threadpool(crud.get_pending_link_by_device, db, device.id)

    if pending_link:
        # Registration Mode
        target_type, target_id = pending_link.target_user_type, pending_link.target_identifier
        try:
            if target_type == models.TargetUserType.STUDENT:
                await run_in_threadpool(crud.update_student_tag_id, db, target_id, tag_id)
            else:
                await run_in_threadpool(crud.update_user_tag_id, db, target_id, tag_id)
        finally:
            await run_in_threadpool(crud.delete_pending_link, db, pending_link.id)
        
        await run_in_threadpool(crud.create_device_log, db, {"device_fk_id": device.id, "tag_id_scanned": tag_id, "action": f"TAG_LINK_SUCCESS: {target_type.value} {target_id}"})
        return {"message": "Tag linked successfully", "user_id": target_id, "user_type": target_type}
    else:
        # Fetching Mode
        student = await run_in_threadpool(crud.get_student_by_tag_id, db, tag_id)
        if student:
            await run_in_threadpool(crud.create_device_log, db, {"device_fk_id": device.id, "tag_id_scanned": tag_id, "action": f"FETCH_SUCCESS: Student {student.student_id}"})
            return await format_student_clearance_details(db, student)

        user = await run_in_threadpool(crud.get_user_by_tag_id, db, tag_id)
        if user:
            await run_in_threadpool(crud.create_device_log, db, {"device_fk_id": device.id, "tag_id_scanned": tag_id, "action": f"FETCH_SUCCESS: User {user.username}"})
            return models.UserResponse.from_orm(user)
        
        await run_in_threadpool(crud.create_device_log, db, {"device_fk_id": device.id, "tag_id_scanned": tag_id, "action": "FETCH_FAIL: Tag not found"})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag ID '{tag_id}' not found.")
