"""
Router for staff and admin clearance operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from src import crud, models
from src.database import get_db
from src.auth import get_current_active_user, get_current_active_staff_user_from_token
from src.utils import format_student_clearance_details

router = APIRouter(
    prefix="/api/clearance",
    tags=["Clearance"],
    dependencies=[Depends(get_current_active_staff_user_from_token)]
)

class ClearanceUpdatePayload(models.BaseModel):
    status: models.ClearanceStatusEnum
    remarks: str | None = None

@router.put("/{student_id_str}", response_model=models.ClearanceDetail)
async def update_student_clearance(
    student_id_str: str,
    payload: ClearanceUpdatePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_staff_user_from_token)
):
    """
    Staff/Admin: Update a student's clearance status for their department.
    """
    if not current_user.department:
        raise HTTPException(status_code=403, detail="Your user account is not assigned to a clearable department.")

    await run_in_threadpool(
        crud.update_clearance_status, db, student_id_str, current_user.department, payload.status, payload.remarks, current_user.id
    )
    
    student_orm = await run_in_threadpool(crud.get_student_by_student_id, db, student_id_str)
    return await format_student_clearance_details(db, student_orm)

@router.delete("/{student_id_str}/{department_str}", response_model=models.ClearanceDetail)
async def reset_student_clearance(
    student_id_str: str,
    department_str: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_staff_user_from_token)
):
    """
    Staff/Admin: Reset a student's clearance status for a department.
    Admins can reset for any department; staff only for their own.
    """
    try:
        target_department = models.ClearanceDepartment(department_str.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"'{department_str}' is not a valid department.")

    if current_user.role != models.UserRole.ADMIN and current_user.department != target_department:
        raise HTTPException(status_code=403, detail=f"You can only reset clearance for your own department.")

    await run_in_threadpool(crud.delete_clearance_status, db, student_id_str, target_department)
    
    student_orm = await run_in_threadpool(crud.get_student_by_student_id, db, student_id_str)
    if not student_orm:
         raise HTTPException(status_code=404, detail="Student not found.")
         
    return await format_student_clearance_details(db, student_orm)
