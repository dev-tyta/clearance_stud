from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as SQLAlchemySessionType
from typing import List, Optional # For type hinting

from src import crud, models
from src.auth import (
    get_current_staff_or_admin_via_tag, # Returns ORM User model (Tag-based)
    get_current_student_via_tag,        # Returns ORM Student model (Tag-based)
    verify_department_access            # Sync utility function
)
from src.database import get_db

router = APIRouter(
    prefix="/api/clearance",
    tags=["clearance"],
)

@router.post("/", response_model=models.ClearanceStatusResponse)
async def update_clearance_status_endpoint( # Async endpoint
    status_data: models.ClearanceStatusCreate,
    db: SQLAlchemySessionType = Depends(get_db),
    # current_user_orm is User ORM model (staff/admin) via Tag-based auth
    current_user_orm: models.User = Depends(get_current_staff_or_admin_via_tag)
):
    """
    Staff/Admin creates or updates a student's clearance status. Uses ORM.
    """
    # crud.get_student_by_student_id is sync
    student_orm = await run_in_threadpool(crud.get_student_by_student_id, db, status_data.student_id)
    if not student_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    # verify_department_access is sync
    # status_data.department is ClearanceDepartment enum from Pydantic
    if not verify_department_access(current_user_orm.role, current_user_orm.department, status_data.department):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user_orm.username}' does not have permission to update clearance for the {status_data.department.value} department."
        )
    
    cleared_by_user_pk = current_user_orm.id # User's primary key

    try:
        # crud.create_or_update_clearance_status is sync, returns ORM model
        updated_status_orm = await run_in_threadpool(
            crud.create_or_update_clearance_status, db, status_data, cleared_by_user_pk
        )
    except HTTPException as e: # Catch known errors from CRUD
        raise e
    return updated_status_orm # Pydantic converts from ORM model


# Helper for student's own clearance view (similar to one in students.py/devices.py)
async def _format_my_clearance_response(
    db: SQLAlchemySessionType,
    student_orm: models.Student # Expect Student ORM model
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

@router.get("/me", response_model=models.ClearanceDetail)
async def get_my_clearance_status( # Async endpoint
    # current_student_orm is Student ORM model via Tag-based auth
    current_student_orm: models.Student = Depends(get_current_student_via_tag),
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    Student retrieves their own complete clearance status via RFID Tag. Uses ORM.
    """
    return await _format_my_clearance_response(db, current_student_orm)

