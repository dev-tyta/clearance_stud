from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, SQLModel

from src.auth import get_current_active_user
from src.database import get_session
from src.models import StudentReadWithClearance

# This is the new request body model for the POST request.
class StudentLookupRequest(SQLModel):
    matric_no: str

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    # This endpoint still requires a user to be logged in.
    dependencies=[Depends(get_current_active_user)]
)

@router.post("/lookup", response_model=StudentReadWithClearance)
def lookup_student_by_matric_no(
    request: StudentLookupRequest,
    db: Session = Depends(get_session)
):
    """
    Endpoint for a logged-in user to retrieve a student's profile
    and clearance information by providing their matriculation number.
    """
    student = student_crud.get_student_by_matric_no(db=db, matric_no=request.matric_no)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Student with the provided matriculation number not found."
        )
    
    return student
