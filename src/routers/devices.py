# In your devices router file (e.g., routers/devices.py)
from fastapi import APIRouter, HTTPException, Depends, status
from src.models import DeviceRegister, DeviceResponse, TagScan, ClearanceDetail # Add ClearanceDetail if not already there
from src import crud
from src.auth import get_verified_device # Import the new dependency
# Import the helper function if it's defined in a shared location
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
