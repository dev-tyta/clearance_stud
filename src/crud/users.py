from sqlmodel import Session, select
from typing import List, Optional

from src.models import User, UserCreate, UserUpdate, RFIDTag
from src.auth import hash_password

# --- Read Operations ---

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieves a user by their primary key ID."""
    return db.get(User, user_id)

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Retrieves a user by their unique username."""
    return db.exec(select(User).where(User.username == username)).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieves a user by their unique email."""
    return db.exec(select(User).where(User.email == email)).first()

def get_user_by_tag_id(db: Session, tag_id: str) -> Optional[User]:
    """Retrieves a user by their linked RFID tag ID."""
    statement = select(User).join(RFIDTag).where(RFIDTag.tag_id == tag_id)
    return db.exec(statement).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Retrieves a paginated list of all users."""
    return db.exec(select(User).offset(skip).limit(limit)).all()

# --- Write Operations ---

def create_user(db: Session, user: UserCreate) -> User:
    """
    Creates a new user.
    - Hashes the password before saving.
    - The router should handle checks for existing username/email to provide clean HTTP errors.
    """
    hashed_pass = hash_password(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_pass,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """
    Updates a user's information.
    - If a new password is provided, it will be hashed.
    """
    db_user = db.get(User, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    
    # Hash password if it's being updated
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[User]:
    """
    Deletes a user from the database.
    The linked RFID tag will also be deleted due to cascade settings.
    """
    db_user = db.get(User, user_id)
    if not db_user:
        return None
    
    db.delete(db_user)
    db.commit()
    return db_user
