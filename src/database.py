import databases
import sqlalchemy
import os
from dotenv import load_dotenv
from datetime import datetime
import enum

# Load environment variables from a .env file
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")

# Check if DATABASE_URL is set
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

# Create a Database instance for asynchronous operations
database = databases.Database(DATABASE_URL)

# Define Enum for User Roles
class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"
    staff = "staff"

# Define Enum for Clearance Departments
class ClearanceDepartment(str, enum.Enum):
    DEPARTMENTAL = "Departmental"
    LIBRARY = "Library"
    BURSARY = "Bursary"
    ALUMNI = "Alumni"

# Define Enum for Clearance Status
class ClearanceStatusEnum(str, enum.Enum):
    NOT_COMPLETED = "NOT_COMPLETED"
    COMPLETED = "COMPLETED"

# Create a MetaData object to hold the database schema
metadata = sqlalchemy.MetaData()

# Define the 'students' table using SQLAlchemy
students = sqlalchemy.Table(
    "students",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("student_id", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("department", sqlalchemy.String),
    sqlalchemy.Column("tag_id", sqlalchemy.String, unique=True, index=True, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

# Define the 'users' table for staff/admin authentication
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("hashed_password", sqlalchemy.String),
    sqlalchemy.Column("role", sqlalchemy.Enum(UserRole), default=UserRole.staff),
    sqlalchemy.Column("department", sqlalchemy.Enum(ClearanceDepartment), nullable=True),  # Which department they manage
    sqlalchemy.Column("tag_id", sqlalchemy.String, unique=True, index=True, nullable=True),  # RFID tag for staff/admin
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

# Define the 'clearance_statuses' table using SQLAlchemy
clearance_statuses = sqlalchemy.Table(
    "clearance_statuses",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("student_id", sqlalchemy.String, sqlalchemy.ForeignKey("students.student_id"), index=True),
    sqlalchemy.Column("department", sqlalchemy.Enum(ClearanceDepartment), index=True),
    sqlalchemy.Column("status", sqlalchemy.Enum(ClearanceStatusEnum), default=ClearanceStatusEnum.NOT_COMPLETED),
    sqlalchemy.Column("remarks", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("cleared_by", sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=True),  # Who cleared it
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
    # Add a unique constraint to prevent duplicate entries for the same student and department
    sqlalchemy.UniqueConstraint('student_id', 'department', name='uq_student_department')
)

# Define the 'device_logs' table to log device activity using SQLAlchemy
device_logs = sqlalchemy.Table(
    "device_logs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("device_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("tag_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("user_type", sqlalchemy.String),  # "student", "staff", "admin"
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("action", sqlalchemy.String),  # e.g., "scan", "register", "clearance_update"
)

# Define the 'devices' table to manage registered ESP32 devices using SQLAlchemy
devices = sqlalchemy.Table(
    "devices",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("device_id", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("location", sqlalchemy.String),  # Re-added location field
    sqlalchemy.Column("api_key", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("last_seen", sqlalchemy.DateTime, nullable=True),
)

# Create a SQLAlchemy engine
engine = sqlalchemy.create_engine(DATABASE_URL)

try:
    print("Attempting to create database tables (if they don't exist)...")
    metadata.create_all(engine)
    print("Database tables creation attempt finished.")
except Exception as e:
    print(f"Error during database table creation: {e}")
    print("Please ensure your database is accessible and the connection string is correct.")

# Database connection lifecycle events
async def connect_db():
    """Connects to the database on application startup."""
    print("Connecting to database...")
    await database.connect()
    print("Database connected.")

async def disconnect_db():
    """Disconnects from the database on application shutdown."""
    print("Disconnecting from database...")
    await database.disconnect()
    print("Database disconnected.")

# Initialize default clearance statuses for new students
async def initialize_student_clearance_statuses(student_id: str):
    """Creates default clearance status entries for all departments when a new student is registered."""
    departments = [
        ClearanceDepartment.DEPARTMENTAL,
        ClearanceDepartment.LIBRARY,
        ClearanceDepartment.BURSARY,
        ClearanceDepartment.ALUMNI
    ]
    
    for dept in departments:
        query = clearance_statuses.insert().values(
            student_id=student_id,
            department=dept,
            status=ClearanceStatusEnum.NOT_COMPLETED
        )
        await database.execute(query)