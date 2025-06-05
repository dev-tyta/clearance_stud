from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as SQLAlchemySessionType
from typing import List, Dict, Any # For type hinting

from src import crud, models
from src.auth import get_current_active_admin_user_from_token # Returns ORM User
from src.database import get_db

router = APIRouter(
    prefix="/api/students",
    tags=["students"],
    # All student management routes require an active admin (token-based)
    dependencies=[Depends(get_current_active_admin_user_from_token)]
)

# Helper function to format clearance details for student endpoints
# This is very similar to the one in devices.py, consider consolidating to a utils.py
async def _format_student_clearance_details_response(
    db: SQLAlchemySessionType,
    student_orm: models.Student
) -> models.ClearanceDetail:
    
    statuses_orm_list = await run_in_threadpool(crud.get_clearance_statuses_by_student_id, db, student_orm.student_id)
    
    clearance_items_models: List[models.ClearanceStatusItem] = []
    overall_status_val = models.OverallClearanceStatusEnum.COMPLETED

    if not statuses_orm_list:
        overall_status_val = models.OverallClearanceStatusEnum.PENDING
    
    for status_orm in statuses_orm_list:
        item = models.ClearanceStatusItem(
            department=status_orm.department,
            status=status_orm.status,
            remarks=status_orm.remarks,
            updated_at=status_orm.updated_at
        )
        clearance_items_models.append(item)
        if item.status != models.ClearanceStatusEnum.COMPLETED:
            overall_status_val = models.OverallClearanceStatusEnum.PENDING
            
    if not statuses_orm_list and overall_status_val == models.OverallClearanceStatusEnum.COMPLETED:
         overall_status_val = models.OverallClearanceStatusEnum.PENDING

    return models.ClearanceDetail(
        student_id=student_orm.student_id,
        name=student_orm.name,
        department=student_orm.department,
        clearance_items=clearance_items_models,
        overall_status=overall_status_val
    )

@router.post("/", response_model=models.StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student_endpoint( # Async endpoint
    student_data: models.StudentCreate,
    db: SQLAlchemySessionType = Depends(get_db),
    # current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token) # For logging
):
    """Admin creates a new student. Uses ORM."""
    try:
        # crud.create_student is sync, handles checks and returns ORM model
        created_student_orm = await run_in_threadpool(crud.create_student, db, student_data)
    except HTTPException as e: # Catch known exceptions from CRUD (e.g., student_id exists)
        raise e
    return created_student_orm # Pydantic converts from ORM model

@router.get("/", response_model=List[models.StudentResponse])
async def get_students_endpoint( # Async endpoint
    skip: int = 0,
    limit: int = 100,
    db: SQLAlchemySessionType = Depends(get_db),
    # current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token)
):
    """Admin gets all students. Uses ORM."""
    # crud.get_all_students is sync
    students_orm_list = await run_in_threadpool(crud.get_all_students, db, skip, limit)
    return students_orm_list # Pydantic converts list of ORM models

@router.get("/{student_id_str}", response_model=models.ClearanceDetail)
async def get_student_clearance_endpoint( # Async endpoint
    student_id_str: str,
    db: SQLAlchemySessionType = Depends(get_db),
    # current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token)
):
    """Admin gets clearance details for a specific student. Uses ORM."""
    # crud.get_student_by_student_id is sync
    student_orm = await run_in_threadpool(crud.get_student_by_student_id, db, student_id_str)
    if not student_orm:
        raise HTTPException(status_code=404, detail="Student not found")
    return await _format_student_clearance_details_response(db, student_orm)

@router.put("/{student_id_str}/link-tag", response_model=models.StudentResponse)
async def link_student_tag_endpoint( # Async endpoint
    student_id_str: str,
    tag_link_request: models.TagLinkRequest,
    db: SQLAlchemySessionType = Depends(get_db),
    # current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token)
):
    """Admin links or updates RFID tag for a student. Uses ORM."""
    try:
        # crud.update_student_tag_id is sync, handles checks
        updated_student_orm = await run_in_threadpool(crud.update_student_tag_id, db, student_id_str, tag_link_request.tag_id)
    except HTTPException as e: # Catch known errors from CRUD
        raise e
    except Exception as e_generic:
        print(f"Unexpected error in link_student_tag_endpoint: {e_generic}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
    return updated_student_orm
