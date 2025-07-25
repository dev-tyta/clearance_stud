from fastapi import HTTPException, status, Header, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.concurrency import run_in_threadpool # For calling sync crud in async auth
from sqlalchemy.orm import Session as SQLAlchemySessionType

from src import crud, models 

from src.database import get_db
from typing import Optional, Dict, Any # Added Any
from datetime import datetime, timedelta
from typing import Union # For type hinting
from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT Configuration - Loaded from models.py (which loads from .env)
SECRET_KEY = models.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token/login") # Path to token endpoint

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # Password hashing context
# Password hashing context from models.py

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    Uses the CryptContext to verify the password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a password using the CryptContext.
    This is used when creating or updating user passwords.
    """
    return pwd_context.hash(password)


# --- JWT Helper Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()}) # Add issued_at time
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: SQLAlchemySessionType = Depends(get_db)
) -> models.User: # Now aims to return the ORM User model
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = models.TokenData(username=username) # Use if TokenData has more fields
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},)
    except jwt.PyJWTError:
        raise credentials_exception
    
    # User is fetched using sync ORM function, so run in threadpool if this dep is used by async endpoint
    user_orm = await run_in_threadpool(crud.get_user_by_username, db, username)
    if user_orm is None:
        raise credentials_exception
    return user_orm # Return the ORM model instance

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user_from_token)
) -> models.User: # Expects and returns ORM User
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_staff_user_from_token(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User: # Expects and returns ORM User
    if current_user.role not in [models.UserRole.STAFF, models.UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff or admin access required")
    return current_user

async def get_current_active_admin_user_from_token(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User: # Expects and returns ORM User
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

# Dependency to get and verify API key from header (Device Authentication)
async def get_verified_device(
    x_api_key: str = Header(..., description="The API Key for the ESP32 device."),
    db: SQLAlchemySessionType = Depends(get_db)
) -> models.Device: # Returns the ORM Device model
    """
    Verifies API key and returns the active ORM Device model.
    """
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    
    # Use run_in_threadpool as crud.get_device_by_api_key is sync
    device_orm = await run_in_threadpool(crud.get_device_by_api_key, db, x_api_key)

    if not device_orm:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")
    if not device_orm.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device is not active.")
    return device_orm


def authenticate_user(
    username: str,
    password: str,
    db: SQLAlchemySessionType = Depends(get_db)
) -> models.User: # Returns ORM User model
    """
    Authenticates a user by username and password.
    Returns the ORM User model if successful, raises HTTPException otherwise.
    """
    user = crud.get_user_by_username(db, username)
    
    if not user:
        return None  # User not found, return None
    
    is_password_valid = verify_password(password, user.hashed_password)
    if not is_password_valid:
        return None

    return user  # Return the ORM User model if password is valid

# Tag-based authentication (User/Student Authentication via RFID tag)
async def authenticate_tag_user_or_student( # Renamed for clarity
    tag_id: str = Header(..., alias="X-User-Tag-ID", description="RFID Tag ID of the user or student"),
    db: SQLAlchemySessionType = Depends(get_db)
) -> Union[models.Student, models.User]: # Returns Student or User ORM model
    """
    Authenticates a tag and returns the corresponding Student or User ORM model.
    Used as a base for tag-based auth dependencies.
    """
    # Run sync ORM calls in threadpool
    student_orm = await run_in_threadpool(crud.get_student_by_tag_id, db, tag_id)
    if student_orm:
        return student_orm # Return Student ORM model
    
    user_orm = await run_in_threadpool(crud.get_user_by_tag_id, db, tag_id) # get_user_by_tag_id checks is_active
    if user_orm: # user_orm already checked for is_active in CRUD
        return user_orm # Return User ORM model
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not registered or associated user/student is inactive.")

# Dependency for current student via Tag ID
async def get_current_student_via_tag(
    authenticated_entity: Union[models.Student, models.User] = Depends(authenticate_tag_user_or_student)
) -> models.Student:
    if not isinstance(authenticated_entity, models.Student):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to students only.")
    return authenticated_entity

# Dependency for current staff or admin via Tag ID
async def get_current_staff_or_admin_via_tag(
    authenticated_entity: Union[models.Student, models.User] = Depends(authenticate_tag_user_or_student)
) -> models.User:
    if not isinstance(authenticated_entity, models.User): # It's a student
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff or admin access required.")
    # authenticated_entity is User ORM model
    if authenticated_entity.role not in [models.UserRole.STAFF, models.UserRole.ADMIN]:
        # This case should ideally not be hit if authenticate_tag_user_or_student is correct
        # and users fetched by tag are always staff/admin.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role is not staff or admin.")
    if not authenticated_entity.is_active: # Double check, though crud.get_user_by_tag_id should handle this
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is inactive.")
    return authenticated_entity

# Dependency for current admin via Tag ID
async def get_current_admin_via_tag(
    current_user: models.User = Depends(get_current_staff_or_admin_via_tag) # Leverages the staff_or_admin check
) -> models.User:
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


# Department Access Verification (this is a utility, not a dependency itself)
def verify_department_access( # Made sync as it's pure logic
    user_role: models.UserRole,
    user_department: Optional[models.ClearanceDepartment],
    target_department: models.ClearanceDepartment
) -> bool:
    if user_role == models.UserRole.ADMIN:
        return True
    if user_role == models.UserRole.STAFF:
        return user_department == target_department
    return False
