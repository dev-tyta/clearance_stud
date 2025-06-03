from fastapi import APIRouter, HTTPException, status
from typing import List
from src import crud
from src.models import StudentCreate, Student, ClearanceDetail

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

