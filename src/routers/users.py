from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.database import get_session
from src.auth import get_current_active_user
from src.models import User, UserRead, Role

# Define the router
router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get("/me", response_model=UserRead)
def read_user_me(
    # This dependency ensures the user is an authenticated Admin or Staff
    # and injects their database object into the 'current_user' parameter.
    current_user: User = Depends(get_current_active_user(required_roles=[Role.ADMIN, Role.STAFF]))
):
    """
    Endpoint for a logged-in user (Admin or Staff) to retrieve their own profile.
    The user is identified via their JWT token.
    """
    # The dependency handles fetching the user, so we just return it.
    return current_user
