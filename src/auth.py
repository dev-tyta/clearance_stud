from fastapi import HTTPException, status, Header, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # Added
from src.database import database, devices # UserRole is in models now
from src import crud
from src.models import UserRole, TagAuth, TokenData # Added TokenData
from typing import Optional
from datetime import datetime, timedelta # Added timedelta
import jwt # Added jwt
from passlib.context import CryptContext # Added for password hashing consistency if needed, though bcrypt is in crud

# JWT Configuration (SHOULD BE MOVED TO A CONFIG FILE/ENV VARS)
SECRET_KEY = "your-super-secret-key"  # IMPORTANT: Change this and keep it secret!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2PasswordBearer for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token/login") # Adjusted tokenUrl

# Password hashing context (align with crud if different, bcrypt is used in crud)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- JWT Helper Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_from_token(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await crud.get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_staff_user_from_token(current_user: dict = Depends(get_current_user_from_token)) -> dict:
    if current_user["role"] not in [UserRole.staff, UserRole.admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff or admin access required")
    if not current_user["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_admin_user_from_token(current_user: dict = Depends(get_current_user_from_token)) -> dict:
    if current_user["role"] != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    if not current_user["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# Dependency to get and verify API key from header
async def get_verified_device(x_api_key: str = Header(..., description="The API Key for the ESP32 device.")):
    """
    Verifies if the provided API key in the 'X-API-KEY' header is valid.
    Returns the device record if valid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in X-API-KEY header",
        )
    
    query = devices.select().where(devices.c.api_key == x_api_key)
    device_row = await database.fetch_one(query)

    if not device_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return device_row

# Tag-based authentication
async def authenticate_tag(tag_id: str) -> TagAuth:
    """
    Authenticates a tag and returns user information and permissions.
    Checks both student and staff/admin tables.
    """
    
    # First check if it's a student tag
    student = await crud.get_student_by_tag_id(tag_id)
    if student:
        return TagAuth(
            user_type="student",
            user_id=student["student_id"],
            name=student["name"],
            department=student["department"],
            role=None,
            permissions=["view_own_clearance"]
        )
    
    # Then check if it's a staff/admin tag
    user = await crud.get_user_by_tag_id(tag_id)
    if user:
        # Determine permissions based on role
        permissions = []
        if user["role"] == UserRole.admin:
            permissions = [
                "view_all_students",
                "manage_all_clearances",
                "view_statistics",
                "manage_users",
                "view_all_departments"
            ]
        elif user["role"] == UserRole.staff:
            permissions = [
                "view_department_students",
                "manage_department_clearances",
                "view_department_statistics"
            ]
        
        return TagAuth(
            user_type=user["role"],
            user_id=user["username"],
            name=user["username"],  # You might want to add a display_name field
            department=user["department"],
            role=user["role"],
            permissions=permissions
        )
    
    # Tag not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tag not registered in the system"
    )

# Dependency for staff authentication (Tag-based)
async def get_current_staff_user(tag_id: str = Header(..., alias="X-User-Tag-ID", description="Tag ID of the staff/admin user")) -> dict:
    """
    Dependency to get current staff or admin user from tag ID in header.
    Ensures the user is staff or admin.
    """
    auth_info = await authenticate_tag(tag_id)
    
    if auth_info.user_type not in [UserRole.staff, UserRole.admin]: # Use UserRole enum for comparison
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required"
        )
    
    # Get full user details
    user = await crud.get_user_by_tag_id(tag_id)
    if not user: # Should not happen if authenticate_tag succeeded for staff/admin
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated staff/admin user not found in user table"
        )
    return user

# Dependency for admin authentication (Tag-based)
async def get_current_admin_user(tag_id: str = Header(..., alias="X-User-Tag-ID", description="Tag ID of the admin user")) -> dict:
    """
    Dependency to get current admin user from tag ID in header.
    Ensures the user is admin.
    """
    auth_info = await authenticate_tag(tag_id)
    
    if auth_info.user_type != UserRole.admin: # Use UserRole enum
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Get full user details
    user = await crud.get_user_by_tag_id(tag_id)
    if not user: # Should not happen
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated admin user not found in user table"
        )
    return user

# Check if staff can manage specific department
async def verify_department_access(user_role: UserRole, user_department: Optional[str], target_department: str) -> bool:
    """
    Verifies if a staff member can access/modify clearances for a specific department.
    Admins can access all departments, staff can only access their assigned department.
    """
    if user_role == UserRole.admin:
        return True
    elif user_role == UserRole.staff:
        return user_department == target_department
    else:
        return False