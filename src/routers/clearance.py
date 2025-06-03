from fastapi import APIRouter, HTTPException, status, Depends
from src import crud
from src.models import ClearanceStatusCreate, ClearanceStatus
# from src.auth import get_current_active_user # Placeholder for admin/staff auth

router = APIRouter(
    prefix="/api/clearance",
    tags=["clearance"],
    # dependencies=[Depends(get_current_active_user)], # TODO: Add proper authentication for these admin/staff endpoints
)

@router.post("/", response_model=ClearanceStatus, summary="Create or update a student's clearance status for a department")
async def update_clearance_status_endpoint(status_data: ClearanceStatusCreate):
    """
    Creates a new clearance status entry for a student and department,
    or updates an existing one.

    **Note:** This endpoint should be protected and only accessible by authorized
    personnel (e.g., department staff, admins).
    """
    # Check if student exists using the crud function
    student = await crud.get_student_by_student_id(status_data.student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    # Create or update the clearance status using the crud function
    return await crud.create_or_update_clearance_status(status_data)