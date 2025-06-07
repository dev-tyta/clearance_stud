from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import enum
import os

Base = declarative_base()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Enums - Values must EXACTLY match the labels in the PostgreSQL ENUM types, case-sensitively.
class UserRole(str, enum.Enum):
    # This one works with lowercase, so we keep it.
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"

class ClearanceStatusEnum(str, enum.Enum):
    # Assuming this enum in the DB uses capitalized labels
    COMPLETED = "COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    PENDING = "PENDING"

class ClearanceDepartment(str, enum.Enum):
    DEPARTMENTAL = "DEPARTMENTAL" 
    LIBRARY = "LIBRARY"
    BURSARY = "BURSARY"
    ALUMNI = "ALUMNI"
class TargetUserType(str, enum.Enum):
    # Assuming this one is lowercase, a common convention
    STUDENT = "student"
    STAFF_ADMIN = "staff_admin"

class OverallClearanceStatusEnum(str, enum.Enum):
    # These are used within the API logic and may not correspond to a DB type
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"

# Helper for SQLAlchemyEnum to ensure values are used
def enum_values_callable(obj):
    return [e.value for e in obj]

# --- ORM Model Definitions ---

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    department = Column(String, nullable=False)
    tag_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole, name="userrole", create_type=False, values_callable=enum_values_callable), default=UserRole.STAFF, nullable=False)
    department = Column(SQLAlchemyEnum(ClearanceDepartment, name="clearancedepartment", create_type=False, values_callable=enum_values_callable), nullable=True)
    tag_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClearanceStatus(Base):
    __tablename__ = "clearance_statuses"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"), index=True, nullable=False)
    department = Column(SQLAlchemyEnum(ClearanceDepartment, name="clearancedepartment", create_type=False, values_callable=enum_values_callable), index=True, nullable=False)
    status = Column(SQLAlchemyEnum(ClearanceStatusEnum, name="clearancestatusenum", create_type=False, values_callable=enum_values_callable), default=ClearanceStatusEnum.NOT_COMPLETED, nullable=False)
    remarks = Column(String, nullable=True)
    cleared_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=True)
    device_id = Column(String, unique=True, index=True, nullable=True)
    location = Column(String, nullable=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)

class PendingTagLink(Base):
    __tablename__ = "pending_tag_links"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id_fk = Column(Integer, ForeignKey("devices.id"), index=True, nullable=False, name="device_id")
    target_user_type = Column(SQLAlchemyEnum(TargetUserType, name="targetusertype", create_type=False, values_callable=enum_values_callable), nullable=False)
    target_identifier = Column(String, nullable=False)
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class DeviceLog(Base):
    __tablename__ = "device_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_fk_id = Column(Integer, ForeignKey("devices.id"), index=True, nullable=True, name="device_id")
    actual_device_id_str = Column(String, index=True, nullable=True)
    tag_id_scanned = Column(String, index=True, nullable=True)
    user_type = Column(String, nullable=True)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

# --- Pydantic Models ---

class StudentCreate(BaseModel):
    student_id: str
    name: str
    email: Optional[EmailStr] = None
    department: str
    tag_id: Optional[str] = None

class StudentResponse(BaseModel):
    id: int
    student_id: str
    name: str
    email: Optional[EmailStr] = None
    department: str
    tag_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class UserBase(BaseModel):
    username: str
    role: UserRole
    department: Optional[ClearanceDepartment] = None
    tag_id: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    department: Optional[ClearanceDepartment] = None
    tag_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class ClearanceStatusCreate(BaseModel):
    student_id: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceStatusItem(BaseModel):
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None
    updated_at: datetime
    class Config: from_attributes = True

class ClearanceStatusResponse(BaseModel):
    id: int
    student_id: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None
    cleared_by: Optional[int] = None
    updated_at: datetime
    created_at: datetime
    class Config: from_attributes = True

class ClearanceDetail(BaseModel):
    student_id: str
    name: str
    department: str
    clearance_items: List[ClearanceStatusItem]
    overall_status: OverallClearanceStatusEnum
    class Config: from_attributes = True

class DeviceRegister(BaseModel):
    device_id: str
    location: str

class DeviceCreateAdmin(BaseModel):
    name: str
    description: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    name: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[str] = None
    api_key: str
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None
    class Config: from_attributes = True

class TagScan(BaseModel):
    device_id: str
    tag_id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None

class TagLinkRequest(BaseModel):
    tag_id: str

class PrepareTagLinkRequest(BaseModel):
    device_identifier: str
    target_user_type: TargetUserType
    target_identifier: str

class ScannedTagSubmit(BaseModel):
    scanned_tag_id: str
