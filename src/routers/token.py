from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.concurrency import run_in_threadpool # To call sync CRUD in async endpoint
from sqlalchemy.orm import Session as SQLAlchemySessionType

from src import crud, models # crud now contains sync ORM functions
from src.auth import create_access_token # JWT creation is sync
from src.database import get_db # Dependency for SQLAlchemy session

router = APIRouter(
    prefix="/api/token",
    tags=["authentication"],
)

@router.post("/login", response_model=models.Token)
async def login_for_access_token( # Endpoint remains async
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    Provides an access token for an authenticated staff or admin user.
    Requires username and password. Uses ORM.
    """
    # crud.get_user_by_username is now sync, call with run_in_threadpool
    user = await run_in_threadpool(crud.get_user_by_username, db, form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # crud.verify_password is sync
    is_password_valid = await run_in_threadpool(crud.verify_password, form_data.password, user.hashed_password)
    if not is_password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token( # create_access_token is sync
        data={"sub": user.username, "role": user.role.value} # user.role is UserRole enum
    )
    return {"access_token": access_token, "token_type": "bearer"}
