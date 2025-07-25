"""
Router for managing users (staff, admins).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List

from src import crud, models
from src.database import get_db
from src.auth import get_current_active_user, get_current_active_admin_user_from_token

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)

@router.post("/", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_active_admin_user_from_token)])
async def create_new_user(user: models.UserCreate, db: Session = Depends(get_db)):
    """
    Admin: Create a new user (staff or admin).
    """
    db_user = await run_in_threadpool(crud.get_user_by_username, db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await run_in_threadpool(crud.create_user, db, user)

@router.get("/", response_model=List[models.UserResponse], dependencies=[Depends(get_current_active_admin_user_from_token)])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Admin: Retrieve a list of all users.
    """
    users = await crud.get_all_users(db, skip=skip, limit=limit) # Assumes get_all_users exists in crud.users
    return users

@router.get("/all", response_model=list[models.UserResponse], dependencies=[Depends(get_current_active_admin_user_from_token)])
async def get_all_users(db: Session = Depends(get_db)):
    """
    Admin: Get a list of all users.
    """
    users = await run_in_threadpool(crud.get_all_users, db)
    return users

@router.get("/me", response_model=models.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """
    Get profile information for the currently authenticated user.
    """
    return current_user

