from sqlmodel import Field, Relationship, SQLModel
from typing import List, Optional
from enum import Enum as PyEnum

# --- Enums for Controlled Vocabularies ---
# Using enums ensures data consistency for categorical fields.

class UserRole(str, PyEnum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"

class Department(str, PyEnum):
    LIBRARY = "library"
    BURSARY = "bursary"
    ALUMNI = "alumni"
    DEPARTMENTAL = "departmental"

class ClearanceProcess(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# --- Database Table Models ---

# Represents a User (Staff or Admin)
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    role: UserRole = Field(default=UserRole.STAFF)
    is_active: bool = Field(default=True)

    # One-to-one relationship with an RFID tag
    rfid_tag: Optional["RFIDTag"] = Relationship(back_populates="user")

# Represents a Student
class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    matric_no: str = Field(index=True, unique=True)
    full_name: str
    email: str = Field(unique=True)
    department: Department
    hashed_password: str

    # One-to-many relationship with clearance statuses
    clearance_statuses: List["ClearanceStatus"] = Relationship(
        back_populates="student", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    # One-to-one relationship with an RFID tag
    rfid_tag: Optional["RFIDTag"] = Relationship(back_populates="student")

# Represents an RFID tag, linking it to either a User or a Student
class RFIDTag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tag_id: str = Field(index=True, unique=True, description="The unique ID from the RFID chip")
    
    # Foreign keys to link to User or Student (only one should be set)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    student_id: Optional[int] = Field(default=None, foreign_key="student.id")

    # Relationships back to the owner of the tag
    user: Optional[User] = Relationship(back_populates="rfid_tag")
    student: Optional[Student] = Relationship(back_populates="rfid_tag")

# Represents a single clearance status for a student in a specific department
class ClearanceStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    department: Department
    status: ClearanceProcess = Field(default=ClearanceProcess.PENDING)
    
    student_id: int = Field(foreign_key="student.id")
    student: Student = Relationship(back_populates="clearance_statuses")

# Represents a physical ESP32 device
class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_name: str = Field(index=True, unique=True)
    api_key: str = Field(unique=True)
    is_active: bool = Field(default=True)
    department: Department

# --- Pydantic Models for API Operations ---
# These models define the shape of data for creating and updating records via the API.

# For Users
class UserCreate(SQLModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.STAFF

class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

# For Students
class StudentCreate(SQLModel):
    matric_no: str
    full_name: str
    email: str
    password: str

class StudentUpdate(SQLModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

# For Devices
class DeviceCreate(SQLModel):
    device_name: str
    department: Department

# For Tag Linking
class TagLink(SQLModel):
    tag_id: str
    matric_no: Optional[str] = None
    username: Optional[str] = None

# For Clearance Updates
class ClearanceUpdate(SQLModel):
    matric_no: str
    department: Department
    status: ClearanceProcess

