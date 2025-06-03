from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Pydantic models for data validation and serialization

class StudentCreate(BaseModel):
    """Model for creating a new student."""
    student_id: str
    name: str
    department: str
    tag_id: str

class Student(StudentCreate):
    """Model for returning student data, including database ID."""
    id: int

class ClearanceStatusCreate(BaseModel):
    """Model for creating or updating a student's clearance status for a specific department."""
    student_id: str
    department: str
    status: bool
    remarks: Optional[str] = None

class ClearanceStatus(ClearanceStatusCreate):
    """Model for returning clearance status data, including database ID and update timestamp."""
    id: int
    updated_at: datetime

class ClearanceDetail(BaseModel):
    """Model for returning a student's full clearance details."""
    student_id: str
    name: str
    department: str
    clearance_items: List[dict] # List of dictionaries representing each clearance item
    overall_status: bool

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
    api_key: str
    timestamp: datetime