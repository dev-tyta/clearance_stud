from sqlmodel import Session, select
from typing import List, Optional

from src.models import User, UserCreate, UserUpdate, RFIDTag
from src.crud.utils import hash_password

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
    """Get user by RFID tag ID."""
    from src.models import RFIDTag
    tag = db.exec(select(RFIDTag).where(RFIDTag.tag_id == tag_id)).first()
    if tag and tag.user_id:
        return db.exec(select(User).where(User.id == tag.user_id)).first()
    return None

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Retrieves a paginated list of all users."""
    return db.exec(select(User).offset(skip).limit(limit)).all()

def create_user(db: Session, user: UserCreate) -> User:
    """Creates a new user and hashes their password."""
    hashed_password = hash_password(user.password)
    db_user = User(
        username=user.username,
        hashed_password=hashed_password,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department=user.department
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user: User, updates: UserUpdate) -> User:
    """Updates a user's information."""
    user = get_user_by_id(db, user_id=user.id)
    if not user:
        return None
    
    update_data = updates.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        # Hash the new password if it's being updated
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    
    user.sqlmodel_update(update_data)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> User | None:
    """Deletes a user by their ID."""
    user_to_delete = db.get(User, user_id)
    if not user_to_delete:
        return None
    db.delete(user_to_delete)
    db.commit()
    # The user object is no longer valid after deletion, so we return the in-memory object
    return user_to_delete
