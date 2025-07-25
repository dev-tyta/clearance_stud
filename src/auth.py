from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timedelta

from src.config import settings
from src.database import get_session
from src.crud import users as user_crud
from src.crud import devices as device_crud
from src.models import User, Role, Device
from src.crud.utils import verify_password, hash_password

# --- Configuration ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)

# --- JWT Token Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- User Authentication ---
def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user by username and password."""
    user = user_crud.get_user_by_username(db, username=username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# --- Dependency for API Key Authentication ---

# def get_api_key(
#     key: str = Depends(api_key_header), db: Session = Depends(get_session)
# ) -> Device:
#     """
#     Dependency to validate the API key from the x-api-key header.
#     Ensures the device is registered in the database.
#     """
#     db_device = device_crud.get_device_by_api_key(db, api_key=key)
#     if not db_device:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or missing API Key",
#         )
#     return db_device


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

async def get_api_key(api_key: str = Security(api_key_header), db: Session = Depends(get_session)):
    """Validate device API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    device = device_crud.get_device_by_api_key(db, api_key=api_key)
    if not device or not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    return api_key
