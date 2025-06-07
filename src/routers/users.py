from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as SQLAlchemySessionType
from typing import List 

from src import crud, models
from src.auth import get_current_active_admin_user_from_token # Returns ORM User
from src.database import get_db
from src.auth import get_current_active_user # Returns ORM User model


router = APIRouter(
    prefix="/api/users",
    tags=["users"],
)

@router.post("/register", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user( # Endpoint remains async
    user_data: models.UserCreate,
    db: SQLAlchemySessionType = Depends(get_db),
   ):
    """
    Admin registers a new staff or admin user. Uses ORM.
    """
    # Role check (user_data.role is already UserRole enum from Pydantic)
    if user_data.role not in [models.UserRole.STAFF, models.UserRole.ADMIN]:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User role must be '{models.UserRole.STAFF.value}' or '{models.UserRole.ADMIN.value}'"
        )
    
    # Check if username already exists  
    try:
        created_user_orm = await run_in_threadpool(crud.create_user, db, user_data)
    except HTTPException as e: # Catch HTTPExceptions raised by CRUD (e.g., username exists)
        raise e
    
    return created_user_orm # Pydantic UserResponse will convert from ORM model

@router.put("/{username_str}/link-tag", response_model=models.UserResponse)
async def link_user_tag_endpoint( # Endpoint remains async
    username_str: str,
    tag_link_request: models.TagLinkRequest,
    db: SQLAlchemySessionType = Depends(get_db),
    current_admin_orm: models.User = Depends(get_current_active_admin_user_from_token) # For logging, if needed
):
    """
    Admin links or updates the RFID tag_id for a specific staff/admin user. Uses ORM.
    """
    try:
        # crud.update_user_tag_id is sync, call with run_in_threadpool
        # It handles tag uniqueness and user existence checks.
        updated_user_orm = await run_in_threadpool(crud.update_user_tag_id, db, username_str, tag_link_request.tag_id)
    except HTTPException as e: # Catch HTTPExceptions from CRUD
        raise e
    except Exception as e:
        # Generic error logging
        print(f"Unexpected error in link_user_tag_endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
        
    return updated_user_orm # Pydantic UserResponse will convert

@router.get("/", response_model=List[models.UserResponse])
async def list_all_users( 
    skip: int = 0,
    limit: int = 100,
    db: SQLAlchemySessionType = Depends(get_db),
):
    """
    Admin lists all staff/admin users with pagination. Uses ORM.
    """
    # crud.get_users is sync, call with run_in_threadpool
    users_orm_list = await run_in_threadpool(crud.get_users, db, skip, limit)
    return users_orm_list # Pydantic will convert the list of ORM User models

@router.get("/users/me", response_model=models.UserResponse, summary="Get current authenticated user details")
async def read_users_me(
    current_user_orm: models.User = Depends(get_current_active_user) # Depends on token auth
):
    """
    Returns the details of the currently authenticated user (via token).
    The user object is already an ORM model instance.
    Pydantic's UserResponse will convert it using from_attributes=True.
    """
    return current_user_orm
