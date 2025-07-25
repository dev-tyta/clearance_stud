"""
CRUD operations for Users (Admins, Staff).
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import bcrypt

from src import models

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_user_by_username(db: Session, username: str) -> models.User | None:
    """
    Retrieves a user by their username.
    """
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    """
    Retrieves a user by their ID.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    """
    Retrieves all users with pagination.
    """
    return db.query(models.User).offset(skip).limit(limit).all()

def get_user_by_tag_id(db: Session, tag_id: str) -> models.User | None:
    """
    Retrieves a user by their TAG_ID.
    """
    return db.query(models.User).filter(models.User.tag_id == tag_id).first()

def update_user_tag_id(db: Session, username: str, new_tag_id: str) -> models.User:
    """
    Updates a user's tag_id.
    """
    # Check if the new tag_id is already in use
    existing_user_with_tag = get_user_by_tag_id(db, new_tag_id)
    if existing_user_with_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag ID '{new_tag_id}' is already assigned to another user."
        )
    
    # Get the user to update
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found."
        )
    
    # Update the tag_id
    user.tag_id = new_tag_id
    db.commit()
    db.refresh(user)
    
    return user

def create_user(db: Session, user_data: models.UserCreate) -> models.User:
    """
    Creates a new user account.
    """
    # Check if username already exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' is already registered."
        )

    # Check if tag_id is already in use (if provided)
    if user_data.tag_id:
        existing_tag_user = get_user_by_tag_id(db, user_data.tag_id)
        if existing_tag_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag ID '{user_data.tag_id}' is already assigned to another user."
            )

    # Hash the password
    hashed_password = hash_password(user_data.password)
    
    # Create new user
    db_user = models.User(
        username=user_data.username,
        name=user_data.name,
        hashed_password=hashed_password,
        role=user_data.role,
        department=user_data.department,
        tag_id=user_data.tag_id,
        is_active=user_data.is_active if user_data.is_active is not None else True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def update_user(db: Session, user_id: int, user_update: models.UserCreate) -> models.User:
    """
    Updates an existing user.
    """
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    # Check if new username is already taken (if changed)
    if user_update.username != db_user.username:
        existing_user = get_user_by_username(db, user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_update.username}' is already taken."
            )

    # Check if new tag_id is already in use (if changed and provided)
    if user_update.tag_id and user_update.tag_id != db_user.tag_id:
        existing_tag_user = get_user_by_tag_id(db, user_update.tag_id)
        if existing_tag_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag ID '{user_update.tag_id}' is already assigned to another user."
            )

    # Update fields
    db_user.username = user_update.username
    db_user.name = user_update.name
    if user_update.password:  # Only update password if provided
        db_user.hashed_password = hash_password(user_update.password)
    db_user.role = user_update.role
    db_user.department = user_update.department
    db_user.tag_id = user_update.tag_id
    db_user.is_active = user_update.is_active if user_update.is_active is not None else True

    db.commit()
    db.refresh(db_user)
    
    return db_user

def delete_user(db: Session, username_to_delete: str, current_admin: models.User) -> models.User:
    """
    Deletes a user, ensuring an admin cannot delete themselves or the last admin.
    """
    if username_to_delete == current_admin.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot delete their own account."
        )

    user_to_delete = get_user_by_username(db, username_to_delete)
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username_to_delete}' not found."
        )

    # Prevent deleting the last admin account
    if user_to_delete.role == models.UserRole.ADMIN:
        admin_count = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete the last remaining admin account."
            )

    # Handle dependencies: set foreign keys to NULL where a user is referenced
    db.query(models.ClearanceStatus).filter(models.ClearanceStatus.cleared_by == user_to_delete.id).update({"cleared_by": None})
    
    # Check if PendingTagLink model exists before trying to delete
    try:
        db.query(models.PendingTagLink).filter(models.PendingTagLink.initiated_by_user_id == user_to_delete.id).delete()
    except AttributeError:
        # PendingTagLink model doesn't exist, skip this cleanup
        pass

    db.delete(user_to_delete)
    db.commit()
    
    return user_to_delete