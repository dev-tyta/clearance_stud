"""
Router for handling all RFID interactions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import Union

from src import crud, models
from src.database import get_db
from src.utils import format_student_clearance_details # Using a utility for DRY code

router = APIRouter(
    prefix="/api/rfid",
    tags=["RFID"],
)

@router.post(
    "/scan",
    response_model=Union[models.ClearanceDetail, models.RfidLinkSuccessResponse, models.UserResponse],
    summary="Unified endpoint for all RFID tag scans."
)
async def handle_rfid_scan(
    scan_data: models.RfidScanRequest,
    db: Session = Depends(get_db),
):
    """
    This endpoint intelligently handles an RFID tag scan.

    - **Registration Mode**: If an admin has prepared the device to link a tag
      to a user, this endpoint will perform the link and return a success message.
    
    - **Fetching Mode**: If the device is not in registration mode, this endpoint
      will look up the user/student by the tag ID and return their details
      (e.g., clearance status for a student).
    """
    # 1. Get the device that sent the scan
    device = await run_in_threadpool(crud.get_device_by_id, db, scan_data.device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{scan_data.device_id}' not found."
        )

    # 2. Check if the device is in "Registration Mode"
    if device.link_for_user_id and device.link_for_user_type:
        user_id_to_link = device.link_for_user_id
        user_type_to_link = device.link_for_user_type

        # Link the tag based on the user type
        if user_type_to_link == models.UserTypeEnum.STUDENT:
            await run_in_threadpool(crud.update_student_tag_id, db, user_id_to_link, scan_data.tag_id)
        elif user_type_to_link == models.UserTypeEnum.USER:
            await run_in_threadpool(crud.update_user_tag_id, db, user_id_to_link, scan_data.tag_id)
        
        # Clear the registration mode from the device
        await run_in_threadpool(crud.clear_device_link_for_user, db, device.device_id_str)
        
        return models.RfidLinkSuccessResponse(
            user_id=user_id_to_link,
            user_type=user_type_to_link
        )
        
    # 3. If not in registration mode, it's "Fetching Mode"
    else:
        # First, check if the tag belongs to a student
        student = await run_in_threadpool(crud.get_student_by_tag_id, db, scan_data.tag_id)
        if student:
            # If a student is found, format and return their full clearance details
            return await format_student_clearance_details(db, student)

        # If not a student, check if it belongs to other users (staff/admin)
        user = await run_in_threadpool(crud.get_user_by_tag_id, db, scan_data.tag_id)
        if user:
            # For a staff/admin, just return their basic profile info
            return models.UserResponse.from_orm(user)
        
        # If the tag is not found anywhere, raise an error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag ID '{scan_data.tag_id}' is not associated with any user."
        )

