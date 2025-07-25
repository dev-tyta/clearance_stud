"""
Pydantic Models for data validation and serialization.
SQLAlchemy Models for database table definitions.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from enum import Enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, DateTime,
    create_engine, Enum as SQLAlchemyEnum
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base

# ==============================================================================
# Shared Enums (used by both SQLAlchemy and Pydantic)
# ==============================================================================

class ClearanceStatusEnum(str, Enum):
    NOT_COMPLETED = "NOT_COMPLETED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class ClearanceDepartment(str, Enum):
    DEPARTMENT = "DEPARTMENT"
    BURSARY = "BURSARY"
    LIBRARY = "LIBRARY"
    ALUMNI = "ALUMNI"

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class TargetUserType(str, Enum):
    STUDENT = "STUDENT"
    STAFF_ADMIN = "STAFF_ADMIN"

class OverallClearanceStatusEnum(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"

class UserTypeEnum(str, Enum):
    """Enum for user types."""
    STUDENT = "student"
    USER = "user"


Base = declarative_base()

class User(Base):
    """Database model for Users (Admins, Staff)."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.STAFF, nullable=False)
    department = Column(SQLAlchemyEnum(ClearanceDepartment), nullable=True)
    is_active = Column(Boolean, default=True)
    tag_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Student(Base):
    """Database model for Students."""
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    tag_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clearance_statuses = relationship("ClearanceStatus", back_populates="student")


class ClearanceStatus(Base):
    """Database model for individual clearance items for a student."""
    __tablename__ = "clearance_statuses"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    department = Column(SQLAlchemyEnum(ClearanceDepartment), nullable=False)
    status = Column(SQLAlchemyEnum(ClearanceStatusEnum), default=ClearanceStatusEnum.NOT_COMPLETED, nullable=False)
    remarks = Column(String, nullable=True)
    cleared_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = relationship("Student", back_populates="clearance_statuses")
    cleared_by_user = relationship("User", foreign_keys=[cleared_by])


class Device(Base):
    """Database model for RFID reader devices."""
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    device_id = Column(String, unique=True, index=True, nullable=True)
    location = Column(String, nullable=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PendingTagLink(Base):
    """Database model for pending tag link requests."""
    __tablename__ = "pending_tag_links"
    id = Column(Integer, primary_key=True, index=True)
    device_id_fk = Column(Integer, ForeignKey("devices.id"), nullable=False)
    target_user_type = Column(SQLAlchemyEnum(TargetUserType), nullable=False)
    target_identifier = Column(String, nullable=False)
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", foreign_keys=[device_id_fk])
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])



class DeviceLog(Base):
    """Database model for device activity logs."""
    __tablename__ = "device_logs"
    id = Column(Integer, primary_key=True, index=True)
    device_fk_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    actual_device_id_str = Column(String, nullable=True)
    tag_id_scanned = Column(String, nullable=True)
    user_type = Column(String, nullable=True)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# --- User and Auth Models ---
class UserBase(BaseModel):
    username: str
    name: str
    role: UserRole = UserRole.STAFF
    department: Optional[ClearanceDepartment] = None
    tag_id: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: UserRole
    department: Optional[ClearanceDepartment] = None
    tag_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Student and Clearance Models ---
class StudentBase(BaseModel):
    student_id: str = Field(..., example="CST/18/123")
    name: str = Field(..., example="John Doe")
    department: str = Field(..., example="Computer Science")

class StudentCreate(StudentBase):
    tag_id: Optional[str] = None

class StudentResponse(StudentBase):
    id: int
    tag_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ClearanceStatusCreate(BaseModel):
    student_id: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceStatusResponse(BaseModel):
    id: int
    student_id: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None
    cleared_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ClearanceStatusItem(BaseModel):
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ClearanceDetail(BaseModel):
    student_id: str
    name: str
    department: str
    overall_status: OverallClearanceStatusEnum
    clearance_items: List[ClearanceStatusItem]

class ClearanceStatusUpdate(BaseModel):
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

# --- Device Models ---
class DeviceCreateAdmin(BaseModel):
    name: str
    description: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[str] = None

class DeviceRegister(BaseModel):
    device_id: str
    location: str

class DeviceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[str] = None
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# --- Tag and Device Models ---
class TagLinkRequest(BaseModel):
    tag_id: str = Field(..., example="A1B2C3D4")
    
class PrepareDeviceRequest(BaseModel):
    device_id_str: str = Field(..., example="RFID-READER-01")
    user_id_str: str # Can be student_id or username
    user_type: UserTypeEnum


class PrepareTagLinkRequest(BaseModel):
    """Request to prepare a device for tag linking."""
    device_identifier: str = Field(..., description="The device ID that will scan for tags")
    target_user_type: TargetUserType = Field(..., description="Type of user (STUDENT or STAFF_ADMIN)")
    target_identifier: str = Field(..., description="Student ID or username to link the tag to")

class PendingTagLinkResponse(BaseModel):
    """Response model for pending tag link information."""
    id: int
    device_id_fk: int
    target_user_type: TargetUserType
    target_identifier: str
    initiated_by_user_id: int
    expires_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScannedTagSubmit(BaseModel):
    """Request when submitting a scanned tag for linking."""
    scanned_tag_id: str = Field(..., description="The scanned RFID tag ID")


# --- New RFID Models ---
class RfidScanRequest(BaseModel):
    """Request body for the unified RFID scan endpoint."""
    tag_id: str = Field(..., description="The ID scanned from the RFID tag.", example="A1B2C3D4")
    device_id: str = Field(..., description="The unique identifier of the RFID reader device.", example="RFID-READER-01")

class RfidLinkSuccessResponse(BaseModel):
    """Success response when a tag is linked."""
    message: str = "Tag linked successfully."
    user_id: str
    user_type: UserTypeEnum

# JWT Configuration
import os
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")