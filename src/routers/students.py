from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from src import crud
from src.models import StudentCreate, Student, StudentUpdate, ClearanceDetail, TagLinkRequest, ClearanceDepartment, ClearanceStatusEnum # Added TagLinkRequest, enums
from src.auth import get_current_active_admin_user_from_token, authenticate_tag, UserRole # Corrected import path

router = APIRouter(
    prefix="/api/students",
    tags=["students"],
)

# Helper function to format clearance details (moved from main.py)
async def _get_formatted_clearance_details(student_id: str, student_info: dict) -> ClearanceDetail:
    statuses = await crud.get_clearance_statuses_by_student_id(student_id)
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
        student_id=student_info["student_id"],
        name=student_info["name"],
        department=student_info["department"],
        clearance_items=clearance_items,
        overall_status=overall_status
    )

@router.post("/", response_model=Student, status_code=status.HTTP_201_CREATED, summary="Create a new student")
async def create_student_endpoint(student: StudentCreate):
    existing_student_by_id = await crud.get_student_by_student_id(student.student_id)
    if existing_student_by_id:
        raise HTTPException(status_code=400, detail="Student ID already registered")
    existing_student_by_tag = await crud.get_student_by_tag_id(student.tag_id)
    if existing_student_by_tag:
        raise HTTPException(status_code=400, detail="Tag ID already assigned to another student")
    return await crud.create_student(student)

@router.get("/", response_model=List[Student], summary="Get all students")
async def get_students_endpoint():
    return await crud.get_all_students()

@router.get("/{student_id}", response_model=ClearanceDetail, summary="Get clearance details for a specific student")
async def get_student_clearance_endpoint(student_id: str):
    student = await crud.get_student_by_student_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return await _get_formatted_clearance_details(student_id, student)

@router.put("/{student_id}/link-tag", response_model=Student, summary="Link or update RFID tag for a student (Admin Only)")
async def link_student_tag_endpoint(
    student_id: str,
    tag_link_request: TagLinkRequest,
    current_admin: dict = Depends(get_current_active_admin_user_from_token) # Corrected dependency usage
):
    """
    Links or updates the RFID tag_id for a specific student.
    If the student already has a tag, it will be overwritten.
    The new tag_id must be unique across all students and users.
    Accessible only by authenticated admin users.
    """
    try:
        updated_student = await crud.update_student_tag_id(student_id, tag_link_request.tag_id)
        # crud.update_student_tag_id raises HTTPException on errors like not found or tag conflict
        return updated_student
    except HTTPException as e:
        raise e
    except Exception as e:
        # Log error e
        # print(f"Unexpected error in link_student_tag_endpoint: {e}") # Basic logging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while linking tag to student.")

# ... Add other student-related endpoints as needed ...

