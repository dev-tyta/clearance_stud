# In your devices router file (e.g., routers/devices.py)
from fastapi import APIRouter, HTTPException, Depends, status, Header
from src.models import DeviceRegister, DeviceResponse, TagScan, ClearanceDetail, ScannedTagSubmit, TargetUserType # Add ClearanceDetail if not already there
from src import crud
from src.auth import get_verified_device # Import the new dependency
# Import the helper function if it\'s defined in a shared location
# from .students_router import _get_formatted_clearance_details # Or from a common utils.py

router = APIRouter(
    prefix="/api", # Or specific prefix like /api/devices
    tags=["devices"],
)

@router.post("/devices/register", response_model=DeviceResponse, summary="Register or re-register an ESP32 device")
async def register_device_endpoint(device_data: DeviceRegister):
    return await crud.register_device(device_data)

@router.post("/scan", response_model=ClearanceDetail, summary="Receive tag scan data from an ESP32 device and return clearance details")
async def scan_tag_endpoint(scan_data: TagScan, verified_device: dict = Depends(get_verified_device)):
    """
    Receives a tag ID from an ESP32 device, verifies the device's API key (from X-API-KEY header),
    logs the scan event, retrieves the student's clearance details, and returns them.
    """
    # Ensure the device_id in the payload matches the one associated with the API key
    if verified_device["device_id"] != scan_data.device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match the provided device_id in the payload."
        )

    await crud.update_device_last_seen(verified_device["device_id"])
    await crud.create_device_log(verified_device["device_id"], scan_data.tag_id, "scan")

    student = await crud.get_student_by_tag_id(scan_data.tag_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this tag")

    # Use the refactored helper function for clearance details
    # This assumes _get_formatted_clearance_details is accessible here
    # You might need to adjust its location (e.g., a common utils.py)
    # For now, let's duplicate the logic slightly for clarity in this example,
    # but ideally, it would call the shared helper.
    statuses = await crud.get_clearance_statuses_by_student_id(student["student_id"])
    clearance_items = []
    overall_status = True
    for status_item in statuses:
        clearance_items.append({
            "department": status_item["department"],
            "status": status_item["status"],
            "remarks": status_item["remarks"],
            "updated_at": status_item["updated_at"].isoformat()
        })
        if not status_item["status"]:
            overall_status = False
    
    return ClearanceDetail(
        student_id=student["student_id"],
        name=student["name"],
        department=student["department"],
        clearance_items=clearance_items,
        overall_status=overall_status
    )

@router.post("/devices/submit-scanned-tag", summary="Submit a scanned tag by an ESP32 device to complete a pending tag link")
async def submit_scanned_tag_endpoint(
    payload: ScannedTagSubmit,
    x_api_key: str = Header(...), # For device authentication via API key
    db: crud.AsyncSession = Depends(crud.get_db_session) # Added database session dependency
):
    """
    Receives a scanned tag_id from a registered ESP32 device.
    If there's an active PendingTagLink for this device, it links the tag_id
    to the specified student or user.
    """
    device = await crud.get_device_by_api_key(db, x_api_key)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key. Device not authenticated."
        )

    pending_link = await crud.get_active_pending_tag_link_by_device_id(db, device["id"])

    if not pending_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active tag linking process found for this device. Please prepare the link first via the admin interface."
        )

    # Ensure the submitted tag is not already in use by another student or user
    existing_student_with_tag = await crud.get_student_by_tag_id(db, payload.scanned_tag_id)
    if existing_student_with_tag and existing_student_with_tag["student_id"] != (pending_link["target_user_id"] if pending_link["target_user_type"] == TargetUserType.STUDENT else None):
        # Delete the pending link as the tag is already taken by someone else not targeted by this link
        await crud.delete_pending_tag_link(db, pending_link["id"])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag ID '{payload.scanned_tag_id}' is already assigned to another student. Pending link cancelled."
        )

    existing_user_with_tag = await crud.get_user_by_tag_id(db, payload.scanned_tag_id)
    if existing_user_with_tag and existing_user_with_tag["username"] != (pending_link["target_user_identifier"] if pending_link["target_user_type"] == TargetUserType.USER else None):
        # Delete the pending link as the tag is already taken by someone else not targeted by this link
        await crud.delete_pending_tag_link(db, pending_link["id"])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag ID '{payload.scanned_tag_id}' is already assigned to another user. Pending link cancelled."
        )
    
    try:
        if pending_link["target_user_type"] == TargetUserType.STUDENT:
            updated_student = await crud.update_student_tag_id(db, pending_link["target_user_id"], payload.scanned_tag_id)
            if not updated_student: # Should not happen if target_user_id was validated
                raise HTTPException(status_code=500, detail="Failed to link tag to student.")
            target_identifier = updated_student["student_id"]
        elif pending_link["target_user_type"] == TargetUserType.USER:
            updated_user = await crud.update_user_tag_id(db, pending_link["target_user_identifier"], payload.scanned_tag_id)
            if not updated_user: # Should not happen if target_user_identifier was validated
                raise HTTPException(status_code=500, detail="Failed to link tag to user.")
            target_identifier = updated_user["username"]
        else:
            # Should be caught by Pydantic validation of PrepareTagLinkRequest, but good to have a fallback
            await crud.delete_pending_tag_link(db, pending_link["id"])
            raise HTTPException(status_code=400, detail="Invalid target user type in pending link.")

        await crud.delete_pending_tag_link(db, pending_link["id"])
        
        # Log device activity
        await crud.update_device_last_seen(db, device["id"])
        await crud.create_device_log(
            db=db,
            device_id=device["id"],
            tag_id_scanned=payload.scanned_tag_id,
            action=f"linked_to_{pending_link['target_user_type'].value}:{target_identifier}"
        )

        return {
            "message": f"Tag ID '{payload.scanned_tag_id}' successfully linked to {pending_link['target_user_type'].value} '{target_identifier}'.",
            "device_id": device["device_id"],
            "tag_id": payload.scanned_tag_id,
            "linked_to_type": pending_link["target_user_type"].value,
            "linked_to_identifier": target_identifier
        }
    except HTTPException as e:
        # If any specific HTTPException was raised during update (e.g. tag already exists from crud), re-raise it
        raise e
    except Exception as e:
        # Catch any other unexpected errors during the linking process
        # Log the error for debugging
        print(f"Error during tag linking: {e}") # Consider more robust logging
        # Optionally, delete the pending link to prevent retries with a problematic state
        # await crud.delete_pending_tag_link(db, pending_link["id"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while linking the tag. The pending link may still be active."
        )
