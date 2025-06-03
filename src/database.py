import databases
import sqlalchemy
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from a .env file
load_dotenv()

# Database setup
# Get the database URL from environment variables
# IMPORTANT: Ensure your .env file has the correct DATABASE_URL for PostgreSQL
# Example: DATABASE_URL="postgresql+asyncpg://user:password@host:port/database_name"
DATABASE_URL = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")

# Check if DATABASE_URL is set
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

# Create a Database instance for asynchronous operations
# The 'databases' library uses the connection string to determine the dialect and driver
database = databases.Database(DATABASE_URL)

# Create a MetaData object to hold the database schema
metadata = sqlalchemy.MetaData()

# Define the 'students' table using SQLAlchemy
students = sqlalchemy.Table(
    "students",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("student_id", sqlalchemy.String, unique=True, index=True), # Added index for faster lookups
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("department", sqlalchemy.String),
    sqlalchemy.Column("tag_id", sqlalchemy.String, unique=True, index=True), # Added index
)

# Define the 'clearance_statuses' table using SQLAlchemy
clearance_statuses = sqlalchemy.Table(
    "clearance_statuses",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("student_id", sqlalchemy.String, index=True), # Added index
    sqlalchemy.Column("department", sqlalchemy.String, index=True), # Added index
    sqlalchemy.Column("status", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("remarks", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, default=datetime.utcnow),
    # Add a unique constraint to prevent duplicate entries for the same student and department
    sqlalchemy.UniqueConstraint('student_id', 'department', name='uq_student_department')
)

# Define the 'device_logs' table to log device activity using SQLAlchemy
device_logs = sqlalchemy.Table(
    "device_logs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("device_id", sqlalchemy.String, index=True), # Added index
    sqlalchemy.Column("tag_id", sqlalchemy.String, index=True), # Added index
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("action", sqlalchemy.String), # e.g., "scan", "register"
)

# Define the 'devices' table to manage registered ESP32 devices using SQLAlchemy (Location Removed)
devices = sqlalchemy.Table(
    "devices",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("device_id", sqlalchemy.String, unique=True, index=True), # Added index
    # Removed: sqlalchemy.Column("location", sqlalchemy.String),
    sqlalchemy.Column("api_key", sqlalchemy.String, unique=True, index=True), # Added index for quick API key lookups
    sqlalchemy.Column("last_seen", sqlalchemy.DateTime, nullable=True),
)

# Create a SQLAlchemy engine (used for creating tables - typically run once)
# Note: For PostgreSQL, check_same_thread=False is not needed.
# This engine is primarily used here for the metadata.create_all call.
engine = sqlalchemy.create_engine(DATABASE_URL)

try:
    print("Attempting to create database tables (if they don't exist)...")
    metadata.create_all(engine)
    print("Database tables creation attempt finished.")
except Exception as e:
    print(f"Error during database table creation: {e}")
    print("Please ensure your Supabase database is accessible and the connection string is correct.")
    print("You might need to manually create tables in Supabase using the provided SQL script.")


# Database connection lifecycle events (to be called by FastAPI)
async def connect_db():
    """Connects to the database on application startup."""
    print("Connecting to database...") # Added print statement for debugging
    await database.connect()
    print("Database connected.") # Added print statement for debugging

async def disconnect_db():
    """Disconnects from the database on application shutdown."""
    print("Disconnecting from database...") # Added print statement for debugging
    await database.disconnect()
    print("Database disconnected.") # Added print statement for debugging
