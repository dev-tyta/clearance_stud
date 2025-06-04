from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import enum
from sqlalchemy import Enum as SQLAlchemyEnum

# Enums
class UserRole(str, enum.Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"

class ClearanceStatusEnum(str, enum.Enum):
    COMPLETED = "COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    PENDING = "PENDING"

class ClearanceDepartment(str, enum.Enum):
    DEPARTMENTAL = "Departmental"
    LIBRARY = "Library"
    BURSARY = "Bursary"
    ALUMNI = "Alumni"

# Student Models
class StudentCreate(BaseModel):
    """Model for creating a new student."""
    student_id: str
    full_name: str
    email: EmailStr
    department: str
    tag_id: Optional[str] = None  # Made optional

class Student(StudentCreate):
    """Model for returning student data, including database ID."""
    id: int
    created_at: datetime

# User Models (Staff/Admin)
class UserCreate(BaseModel):
    """Model for creating a new staff/admin user."""
    username: str
    password: str
    role: UserRole
    department: Optional[ClearanceDepartment] = None  # Which department they manage
    tag_id: Optional[str] = None  # RFID tag for authentication

class UserResponse(BaseModel):
    """Model for returning user data."""
    id: int
    username: str
    role: UserRole
    department: Optional[ClearanceDepartment] = None
    tag_id: Optional[str] = None
    is_active: bool
    created_at: datetime

# Clearance Models
class ClearanceStatusCreate(BaseModel):
    """Model for creating or updating a student's clearance status for a specific department."""
    student_id: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceStatusUpdate(BaseModel):
    """Model for staff/admin updating clearance status."""
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceStatus(BaseModel):
    """Model for returning clearance status data."""
    id: int
    student_id: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None
    cleared_by: Optional[int] = None
    updated_at: datetime
    created_at: datetime

class ClearanceDetail(BaseModel):
    """Model for returning a student's full clearance details."""
    student_id: str
    name: str
    department: str
    clearance_items: List[dict]
    overall_status: str  # "COMPLETED" or "PENDING"

# Device Models
class DeviceRegister(BaseModel):
    """Model for registering a new ESP32 device."""
    device_id: str
    location: str

class DeviceResponse(DeviceRegister):
    """Model for returning device registration details, including the API key."""
    api_key: str

class TagScan(BaseModel):
    """Model for data received from an ESP32 device after scanning a tag."""
    device_id: str
    tag_id: str
    timestamp: Optional[datetime] = None

# Authentication Models
class TagAuth(BaseModel):
    """Model for tag-based authentication response."""
    user_type: str  # "student", "staff", "admin"
    user_id: str
    name: str
    department: Optional[str] = None
    role: Optional[UserRole] = None
    permissions: List[str]

# Admin Dashboard Models
class StudentListItem(BaseModel):
    """Model for student list in admin dashboard."""
    student_id: str
    name: str
    department: str
    overall_clearance_status: str
    pending_departments: List[str]

class DepartmentClearanceStats(BaseModel):
    """Model for department clearance statistics."""
    department: ClearanceDepartment
    total_students: int
    completed: int
    pending: int
    completion_rate: float

# Token Models for Password-based Authentication
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Request model for linking a tag
class TagLinkRequest(BaseModel):
    tag_id: str

class TargetUserType(str, enum.Enum):
    STUDENT = "student"
    STAFF_ADMIN = "staff_admin"

class Device(BaseModel):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PendingTagLink(BaseModel):
    __tablename__ = "pending_tag_links"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_api_key = Column(String, ForeignKey("devices.api_key"), index=True, nullable=False) # Assuming devices table and api_key as unique identifier
    target_user_type = Column(SQLAlchemyEnum(TargetUserType), nullable=False)
    target_identifier = Column(String, nullable=False) # student_id for students, username for staff/admin
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationships (optional, but good for ORM use)
    # initiated_by = relationship("User")
    # device = relationship("Device", foreign_keys=[device_api_key], primaryjoin="PendingTagLink.device_api_key == Device.api_key")


class DeviceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class DeviceResponse(DeviceCreate):
    id: int
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class PrepareTagLinkRequest(BaseModel):
    device_api_key: str
    target_user_type: TargetUserType
    target_identifier: str # student_id or username

class ScannedTagSubmit(BaseModel):
    scanned_tag_id: str