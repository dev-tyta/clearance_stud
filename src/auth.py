from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from typing import List, Optional

from src.config import settings
from src.database import get_session
from src.crud import users as user_crud
from src.crud import devices as device_crud
from src.models import User, Role, Device

# --- Configuration ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)

# --- JWT Token Functions ---
def create_access_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Password Hashing ---
def verify_password(plain_password, hashed_password):
    return settings.PWD_CONTEXT.verify(plain_password, hashed_password)

def hash_password(password):
    return settings.PWD_CONTEXT.hash(password)

# --- Dependency for API Key Authentication ---

def get_api_key(
    key: str = Depends(api_key_header), db: Session = Depends(get_session)
) -> Device:
    """
    Dependency to validate the API key from the x-api-key header.
    Ensures the device is registered in the database.
    """
    db_device = device_crud.get_device_by_api_key(db, api_key=key)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return db_device


# --- Dependency for User Authentication and Authorization ---
def get_current_active_user(required_roles: List[Role] = None):
    def dependency(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)
    ) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = user_crud.get_user_by_username(db, username=username)
        if user is None:
            raise credentials_exception

        # Check for roles if required
        if required_roles:
            is_authorized = any(role == user.role for role in required_roles)
            if not is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The user does not have adequate privileges",
                )
        return user

    return dependency
