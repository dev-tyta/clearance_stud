from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from src.database import get_session
from src.auth import get_current_active_user
from src.models import User, Role, ClearanceStatus, ClearanceUpdate, ClearanceStatusRead
from src.crud import clearance as clearance_crud

router = APIRouter(
    prefix="/clearance",
    tags=["Clearance"],
    dependencies=[Depends(get_current_active_user(required_roles=[Role.STAFF, Role.ADMIN]))],
)

@router.put("/update", response_model=ClearanceStatusRead)
def update_student_clearance_status(
    clearance_update: ClearanceUpdate, 
    db: Session = Depends(get_session),
    # The current_user object is injected by the dependency
    current_user: User = Depends(get_current_active_user(required_roles=[Role.STAFF, Role.ADMIN]))
):
    """
    Endpoint for staff to update a student's clearance status.
    A staff member can only approve for their own department.
    (Future enhancement could enforce this rule more strictly).
    """
    # A potential security check: ensure staff's department matches clearance_update.department
    # For now, we trust the role.
    
    updated_status = clearance_crud.update_clearance_status(db, clearance_update)
    
    if not updated_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clearance record found for student {clearance_update.matric_no} in department {clearance_update.department}"
        )
        
    return updated_status
