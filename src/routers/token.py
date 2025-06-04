from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from src import crud
from src.auth import create_access_token, get_current_user_from_token # Assuming verify_password is in crud
from src.models import Token, UserResponse # UserResponse for returning user info without password

router = APIRouter(
    prefix="/api/token",
    tags=["authentication"],
)

@router.post("/login", response_model=Token, summary="Login for existing user (staff/admin) to get access token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Provides an access token for an authenticated staff or admin user.
    Requires username and password.
    """
    user = await crud.get_user_by_username(form_data.username)
    if not user or not await crud.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"].value} # Include role in token
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse, summary="Get current authenticated user details")
async def read_users_me(current_user: dict = Depends(get_current_user_from_token)):
    """
    Returns the details of the currently authenticated user (via token).
    """
    # We can map the user dictionary to UserResponse if needed, or ensure get_user_by_username returns a compatible dict
    # For now, assuming the dict returned by get_current_user_from_token is compatible enough
    # or that UserResponse can be instantiated from it.
    return UserResponse(**current_user)
