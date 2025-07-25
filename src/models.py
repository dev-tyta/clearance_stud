from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Session, select
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

class Status(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# --- Database Table Models ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    role: Role
    rfid_tag: Optional["RFIDTag"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    matric_no: str = Field(index=True, unique=True)
    department: Department
    rfid_tag: Optional["RFIDTag"] = Relationship(back_populates="student", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    clearance_statuses: List["ClearanceStatus"] = Relationship(back_populates="student", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class ClearanceStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    department: ClearanceDepartment
    status: Status = Status.PENDING
    student_id: int = Field(foreign_key="student.id")
    student: Student = Relationship(back_populates="clearance_statuses")

class RFIDTag(SQLModel, table=True):
    tag_id: str = Field(primary_key=True, index=True)
    student_id: Optional[int] = Field(default=None, foreign_key="student.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    student: Optional[Student] = Relationship(back_populates="rfid_tag")
    user: Optional[User] = Relationship(back_populates="rfid_tag")

class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    api_key: str = Field(unique=True, index=True)
    location: str

# --- Pydantic Models for API Operations ---

# User Models
class UserCreate(SQLModel):
    username: str
    password: str
    role: Role

class UserRead(SQLModel):
    id: int
    username: str
    role: Role

# Student Models
class StudentCreate(SQLModel):
    full_name: str
    matric_no: str
    department: Department
    username: str # For creating the associated user account
    password: str

class StudentUpdate(SQLModel):
    full_name: Optional[str] = None
    department: Optional[Department] = None

class StudentRead(SQLModel):
    id: int
    full_name: str
    matric_no: str
    department: Department

# Clearance Status Models
class ClearanceStatusRead(SQLModel):
    department: ClearanceDepartment
    status: Status

class ClearanceStatusUpdate(SQLModel):
    status: Status
    matric_no: str

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
    status: str # e.g., "found", "unregistered", "error"
    full_name: Optional[str] = None
    message: Optional[str] = None
    clearance: Optional[str] = None # e.g., "Approved", "Pending", "Rejected"


# Device Models
class DeviceCreate(SQLModel):
    location: str

class DeviceRead(SQLModel):
    id: int
    api_key: str
    location: str
