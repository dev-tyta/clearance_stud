from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlmodel import Session

from src.database import get_session
from src.auth import get_api_key
from src.models import RFIDStatusResponse, RFIDScanRequest
from src.crud import students as student_crud
from src.crud import users as user_crud

# Define the router and the API key security scheme
router = APIRouter(prefix="/rfid", tags=["RFID"])
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

@router.post("/check-status", response_model=RFIDStatusResponse)
def check_rfid_status(
    scan_data: RFIDScanRequest,
    db: Session = Depends(get_session),
    # This dependency ensures the request comes from a valid, registered device
    api_key: str = Security(get_api_key),
):
    """
    Public endpoint for hardware devices to check the status of a scanned RFID tag.
    The device must provide a valid API key in the 'x-api-key' header.
    """
    tag_id = scan_data.tag_id

    # 1. Check if the tag belongs to a student
    student = student_crud.get_student_by_tag_id(db, tag_id=tag_id)
    if student:
        # Check overall clearance status
        is_cleared = all(
            status.status == "approved" for status in student.clearance_statuses
        )
        clearance_status_str = "Fully Cleared" if is_cleared else "Pending Clearance"
        
        return RFIDStatusResponse(
            status="found",
            full_name=student.full_name,
            entity_type="Student",
            clearance_status=clearance_status_str,
        )

    # 2. If not a student, check if it belongs to a user (staff/admin)
    user = user_crud.get_user_by_tag_id(db, tag_id=tag_id)
    if user:
        return RFIDStatusResponse(
            status="found",
            full_name=user.full_name,
            entity_type=user.role.value, # e.g. "Admin" or "Staff"
            clearance_status="N/A",
        )

    # 3. If the tag is not linked to anyone
    return RFIDStatusResponse(
        status="unregistered",
        full_name=None,
        entity_type=None,
        clearance_status=None,
    )
