from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from src.database import get_session
from src.auth import get_current_active_student
from src.models import Student, StudentReadWithClearance

router = APIRouter(
    prefix="/students",
    tags=["Students"],
)

@router.get("/me", response_model=StudentReadWithClearance)
def read_student_me(
    # This dependency ensures the user is an authenticated student
    # and injects their database object into the 'current_student' parameter.
    current_student: Student = Depends(get_current_active_student)
):
    """
    Endpoint for a logged-in student to retrieve their own profile
    and clearance information. The user is identified via their JWT token.
    """
    # Because the dependency returns the full student object, we can just return it.
    # No need for another database call.
    if not current_student:
         # This should not happen if the dependency is set up correctly
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return current_student

