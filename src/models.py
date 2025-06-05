from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta # Added timedelta
import enum
import os # For loading SECRET_KEY

Base = declarative_base()

# Environment variable for SECRET_KEY
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-default-secret-key-for-dev-only-CHANGE-ME")
if JWT_SECRET_KEY == "your-default-secret-key-for-dev-only-CHANGE-ME":
    print("WARNING: Using default JWT_SECRET_KEY. Please set a strong JWT_SECRET_KEY environment variable for production.")


# Enums - Centralized Definition
class UserRole(str, enum.Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"

class ClearanceStatusEnum(str, enum.Enum):
    COMPLETED = "COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    PENDING = "PENDING" # Maintained if used, but overall might simplify to COMPLETED/NOT_COMPLETED

class ClearanceDepartment(str, enum.Enum):
    DEPARTMENTAL = "Departmental"
    LIBRARY = "Library"
    BURSARY = "Bursary"
    ALUMNI = "Alumni"

class TargetUserType(str, enum.Enum):
    STUDENT = "student"
    STAFF_ADMIN = "staff_admin"

class OverallClearanceStatusEnum(str, enum.Enum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"

# SQLAlchemy ORM Model for Student
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True) # Added email, make nullable or not based on requirements
    department = Column(String, nullable=False)
    tag_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to ClearanceStatus (optional, if needed for ORM queries)
    # clearance_statuses = relationship("ClearanceStatus", back_populates="student")


# SQLAlchemy ORM Model for User (Staff/Admin)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.STAFF, nullable=False) # Uses centralized UserRole
    department = Column(SQLAlchemyEnum(ClearanceDepartment), nullable=True) # Uses centralized ClearanceDepartment
    tag_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (optional)
    # clearance_actions_by = relationship("ClearanceStatus", back_populates="cleared_by_user")
    # pending_tags_initiated = relationship("PendingTagLink", back_populates="initiated_by")

# SQLAlchemy ORM Model for ClearanceStatus
class ClearanceStatus(Base):
    __tablename__ = "clearance_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    # student_id_fk = Column(String, ForeignKey("students.student_id"), index=True, name="student_id") # Explicit column name
    # Changed student_id to directly reference the column in students table if that's its name
    student_id = Column(String, ForeignKey("students.student_id"), index=True, nullable=False)
    department = Column(SQLAlchemyEnum(ClearanceDepartment), index=True, nullable=False) # Uses centralized ClearanceDepartment
    status = Column(SQLAlchemyEnum(ClearanceStatusEnum), default=ClearanceStatusEnum.NOT_COMPLETED, nullable=False) # Uses centralized ClearanceStatusEnum
    remarks = Column(String, nullable=True)
    # cleared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, name="cleared_by") # Explicit column name
    # Changed cleared_by to directly reference the column in users table
    cleared_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (optional)
    # student = relationship("Student", back_populates="clearance_statuses")
    # cleared_by_user = relationship("User", back_populates="clearance_actions_by")

# SQLAlchemy ORM Model for Device
class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=True)
    device_id = Column(String, unique=True, index=True, nullable=True) # ESP32's own ID
    location = Column(String, nullable=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)

    # Relationship
    # pending_tag_links = relationship("PendingTagLink", back_populates="device")

# SQLAlchemy ORM Model for PendingTagLink
class PendingTagLink(Base):
    __tablename__ = "pending_tag_links"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id_fk = Column(Integer, ForeignKey("devices.id"), index=True, nullable=False, name="device_id") # Correct: Links to Device PK
    target_user_type = Column(SQLAlchemyEnum(TargetUserType), nullable=False) # Uses centralized TargetUserType
    target_identifier = Column(String, nullable=False) # student_id or username
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationships (optional, but good for ORM use)
    # initiated_by = relationship("User", back_populates="pending_tags_initiated")
    # device = relationship("Device", foreign_keys=[device_id_fk], back_populates="pending_tag_links")

# SQLAlchemy ORM Model for DeviceLog
class DeviceLog(Base):
    __tablename__ = "device_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Assuming device_id here refers to the PK of the devices table
    # If it refers to the string device_id from ESP32, then it's not a direct FK to devices.id
    # For FK relationship, it should be:
    device_fk_id = Column(Integer, ForeignKey("devices.id"), index=True, nullable=True, name="device_id") # FK to devices.id
    # Store the string device_id separately if needed for direct query without join, or rely on relationship
    actual_device_id_str = Column(String, index=True, nullable=True) # The ESP32's device_id string
    tag_id_scanned = Column(String, index=True, nullable=True)
    user_type = Column(String, nullable=True)  # "student", "staff", "admin", "unknown"
    action = Column(String, nullable=False)  # e.g., "scan", "register", "clearance_update", "tag_link_success"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Optional: Add relationship to Device table
    # device = relationship("Device")


# --- Pydantic Models ---

# Student Models
class StudentCreate(BaseModel):
    student_id: str
    name: str
    email: Optional[EmailStr] = None # Added email, make optional or not based on requirements
    department: str
    tag_id: Optional[str] = None

class StudentResponse(StudentCreate):
    id: int
    created_at: datetime
    # email: Optional[EmailStr] = None # Ensure this is present if in StudentCreate and DB

    class Config:
        from_attributes = True

# User Models (Staff/Admin)
class UserBase(BaseModel):
    username: str
    role: UserRole # Uses centralized UserRole
    department: Optional[ClearanceDepartment] = None # Uses centralized ClearanceDepartment
    tag_id: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole # Uses centralized UserRole
    department: Optional[ClearanceDepartment] = None # Uses centralized ClearanceDepartment
    tag_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Clearance Models
class ClearanceStatusCreate(BaseModel):
    student_id: str
    department: ClearanceDepartment # Uses centralized ClearanceDepartment
    status: ClearanceStatusEnum # Uses centralized ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceStatusUpdate(BaseModel):
    status: ClearanceStatusEnum # Uses centralized ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceStatusItem(BaseModel): # For individual items in ClearanceDetail
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None
    updated_at: datetime

class ClearanceStatusResponse(BaseModel):
    id: int
    student_id: str
    department: ClearanceDepartment # Uses centralized ClearanceDepartment
    status: ClearanceStatusEnum # Uses centralized ClearanceStatusEnum
    remarks: Optional[str] = None
    cleared_by: Optional[int] = None # Matches ORM model
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class ClearanceDetail(BaseModel):
    student_id: str
    name: str
    department: str # Student's own department
    clearance_items: List[ClearanceStatusItem] # Changed to use specific model
    overall_status: OverallClearanceStatusEnum # Use Enum for overall status

# Device Models
class DeviceRegister(BaseModel): # For ESP32 self-registration
    device_id: str # ESP32's unique hardware ID
    location: str

class DeviceCreateAdmin(BaseModel): # For admin creating a device record
    name: str
    description: Optional[str] = None
    device_id: Optional[str] = None # Optional: ESP32's unique hardware ID if known
    location: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    name: Optional[str] = None
    device_id: Optional[str] = None # ESP32's hardware ID
    location: Optional[str] = None
    api_key: str # This is sensitive, consider if it should always be returned
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime # Should be onupdate
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True

class TagScan(BaseModel): # From ESP32 device
    device_id: str # ESP32's hardware ID that performed the scan
    tag_id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

# Authentication Models
class TagAuth(BaseModel):
    user_type: str  # "student", "staff", "admin" - could be UserRole.value
    user_id: str # student_id for student, username for staff/admin
    name: str
    department: Optional[str] = None # For student or staff
    role: Optional[UserRole] = None # For staff/admin
    # permissions: List[str] # Simplified: role implies permissions on backend

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    # You can add more claims like role here if needed from token
    # role: Optional[UserRole] = None

# Tag Linking Models
class TagLinkRequest(BaseModel): # For admin to link a tag to student/user
    tag_id: str # The new tag_id to be linked

class PrepareTagLinkRequest(BaseModel): # Admin prepares a device for tag linking
    device_identifier: str # Can be Device.id (PK as string) or Device.device_id (string from ESP)
    target_user_type: TargetUserType # Uses centralized TargetUserType
    target_identifier: str # student_id for student, username for staff/admin

class ScannedTagSubmit(BaseModel): # ESP32 submits the tag it scanned
    scanned_tag_id: str
