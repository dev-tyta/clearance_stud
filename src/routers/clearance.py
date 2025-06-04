from fastapi import APIRouter, HTTPException, status, Depends
from src import crud
from src.models import ClearanceStatusCreate, ClearanceStatus, UserRole, ClearanceDetail # Added UserRole and ClearanceDetail
from src.auth import get_current_staff_user, verify_department_access, authenticate_tag # Added verify_department_access, authenticate_tag

router = APIRouter(
    prefix="/api/clearance",
    tags=["clearance"],
)

@router.post("/", response_model=ClearanceStatus, summary="Create or update a student's clearance status for a department by Staff/Admin")
async def update_clearance_status_endpoint(
    status_data: ClearanceStatusCreate,
    current_user: dict = Depends(get_current_staff_user) # 1. Secure endpoint
):
    """
    Creates a new clearance status entry for a student and department,
    or updates an existing one.

    Accessible only by authenticated Staff or Admin users.
    Staff users can only update clearance for their assigned department.
    """
    # Check if student exists
    student = await crud.get_student_by_student_id(status_data.student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    # 2. Implement Department-Level Access Control
    user_role = UserRole(current_user["role"]) # Cast to UserRole enum
    user_department = current_user.get("department")
    target_department = status_data.department

    if not await verify_department_access(user_role, user_department, target_department):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to update clearance for the {target_department.value} department."
        )

    # Create or update the clearance status, passing the current_user's ID as cleared_by
    return await crud.create_or_update_clearance_status(status_data, cleared_by_user_id=current_user["id"])

# 3. Endpoint for students to view their own clearance status
@router.get("/me", response_model=ClearanceDetail, summary="Get own complete clearance status (for students)")
async def get_my_clearance_status(
    current_user_auth: dict = Depends(authenticate_tag) # Authenticate based on X-User-Tag-ID
):
    """
    Retrieves the complete clearance status for the currently authenticated student.
    The student is identified by their RFID tag ID passed in the 'X-User-Tag-ID' header.
    """
    if current_user_auth.user_type != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to students only."
        )

    student_id = current_user_auth.user_id # This is student_id from TagAuth model

    # Fetch student details
    student_record = await crud.get_student_by_student_id(student_id)
    if not student_record:
        # This case should ideally not be reached if authenticate_tag was successful
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student record not found.")

    # Fetch all clearance statuses for this student
    clearance_statuses = await crud.get_clearance_statuses_by_student_id(student_id)

    clearance_items = []
    all_completed = True
    if not clearance_statuses: # Handle case where student has no clearance entries yet (should be initialized)
        all_completed = False # Or handle as per system logic, perhaps initialize them here if missing
    
    for status_item in clearance_statuses:
        clearance_items.append({
            "department": status_item["department"],
            "status": status_item["status"],
            "remarks": status_item["remarks"],
            "updated_at": status_item["updated_at"]
        })
        if status_item["status"] != "COMPLETED":
            all_completed = False

    return ClearanceDetail(
        student_id=student_record["student_id"],
        name=student_record["name"],
        department=student_record["department"],
        clearance_items=clearance_items,
        overall_status="COMPLETED" if all_completed and clearance_items else "PENDING"
    )