from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum

# --- Enums for choices ---

class Role(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"

class Department(str, Enum):
    COMPUTER_SCIENCE = "Computer Science"
    ENGINEERING = "Engineering"
    BUSINESS_ADMIN = "Business Administration"
    LAW = "Law"
    MEDICINE = "Medicine"

class ClearanceDepartment(str, Enum):
    LIBRARY = "Library"
    STUDENT_AFFAIRS = "Student Affairs"
    BURSARY = "Bursary"
    ACADEMIC_AFFAIRS = "Academic Affairs"
    HEALTH_CENTER = "Health Center"

class ClearanceStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# --- Database Table Models ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    full_name: str
    hashed_password: str
    role: Role
    department: Optional[Department] = None # For staff members
    rfid_tag: Optional["RFIDTag"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    matric_no: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    department: Department
    # A student's login is handled by their associated User record, not directly here.
    rfid_tag: Optional["RFIDTag"] = Relationship(back_populates="student", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    clearance_statuses: List["ClearanceStatus"] = Relationship(back_populates="student", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class ClearanceStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    department: ClearanceDepartment
    status: ClearanceStatusEnum = Field(default=ClearanceStatusEnum.PENDING)
    remarks: Optional[str] = None
    student_id: int = Field(foreign_key="student.id")
    student: "Student" = Relationship(back_populates="clearance_statuses")

class RFIDTag(SQLModel, table=True):
    tag_id: str = Field(primary_key=True, index=True)
    student_id: Optional[int] = Field(default=None, foreign_key="student.id", unique=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", unique=True)
    student: Optional["Student"] = Relationship(back_populates="rfid_tag")
    user: Optional["User"] = Relationship(back_populates="rfid_tag")

class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_name: str = Field(unique=True, index=True)
    api_key: str = Field(unique=True, index=True)
    location: str
    is_active: bool = Field(default=True)

# --- Pydantic Models for API Operations ---

# Token Model
class Token(SQLModel):
    access_token: str
    token_type: str

# User Models
class UserCreate(SQLModel):
    username: str
    password: str
    email: str
    full_name: str
    role: Role
    department: Optional[Department] = None

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[Role] = None
    department: Optional[Department] = None
    password: Optional[str] = None

class UserRead(SQLModel):
    id: int
    username: str
    email: str
    full_name: str
    role: Role
    department: Optional[Department] = None

# Student Models
class StudentCreate(SQLModel):
    full_name: str
    matric_no: str
    email: str
    department: Department
    password: str # This will be used to create the associated User account for the student

class StudentUpdate(SQLModel):
    full_name: Optional[str] = None
    department: Optional[Department] = None
    email: Optional[str] = None

class StudentRead(SQLModel):
    id: int
    full_name: str
    matric_no: str
    department: Department

# Clearance Status Models
class ClearanceStatusRead(SQLModel):
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

class ClearanceUpdate(SQLModel):
    matric_no: str
    department: ClearanceDepartment
    status: ClearanceStatusEnum
    remarks: Optional[str] = None

# Combined Read Model
class StudentReadWithClearance(StudentRead):
    clearance_statuses: List[ClearanceStatusRead] = []
    rfid_tag: Optional["RFIDTagRead"] = None

# RFID Tag Models
class RFIDTagRead(SQLModel):
    tag_id: str
    student_id: Optional[int] = None
    user_id: Optional[int] = None

class TagLink(SQLModel):
    tag_id: str
    matric_no: Optional[str] = None
    username: Optional[str] = None

# RFID Device-Specific Models
class RFIDScanRequest(SQLModel):
    tag_id: str

class RFIDStatusResponse(SQLModel):
    status: str
    full_name: Optional[str] = None
    message: Optional[str] = None
    clearance: Optional[str] = None

class TagScan(SQLModel):
    tag_id: str

# Device Models
class DeviceCreate(SQLModel):
    device_name: str
    location: str

class DeviceRead(SQLModel):
    id: int
    device_name: str
    api_key: str
    location: str
    is_active: bool
