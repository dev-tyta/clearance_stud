from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# Correctly import the database table creation function
from src.database import create_db_and_tables
# Import all the necessary routers for the application
from src.routers import students, devices, clearance, token, users, admin

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Handles application startup and shutdown events.
    - On startup, it ensures that all necessary database tables are created.
    - On shutdown, it can be used for cleanup tasks.
    """
    print("Application startup: Initializing...")
    # Correctly call the function to create database tables
    create_db_and_tables()
    print("Application startup: Database tables checked/created.")
    yield
    print("Application shutdown: Cleaning up.")


# Initialize the FastAPI application instance with metadata for documentation
app = FastAPI(
    title="Undergraduate Clearance System API",
    description="""
    A comprehensive API for managing student clearance processes with RFID authentication.
    
    ## Features
    * **RFID Authentication**: Students and staff use RFID tags for quick access.
    * **Multi-Department Clearance**: Support for Library, Bursary, Alumni, and Departmental clearances.
    * **Device Management**: Secure management of ESP32 RFID readers via API keys.
    * **Role-Based Access Control**: Differentiated permissions for Students, Staff, and Administrators.
    * **Real-Time Tracking**: Live updates on clearance status with comprehensive logging.
    
    ## Authentication Methods
    * **JWT Tokens**: For web interfaces and administrative API access.
    * **RFID Tags**: For quick, on-premise authentication of students and staff.
    * **Device API Keys**: For secure communication with hardware like ESP32 RFID readers.
    """,
    version="2.0.1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS (Cross-Origin Resource Sharing) middleware
# This allows the frontend (like the Streamlit app) to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Allows all origins, consider restricting in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Include all the API routers into the main application
# Each router handles a specific domain of the application (e.g., students, devices)
print("Including API routers...")
app.include_router(admin.router)
app.include_router(clearance.router)
app.include_router(devices.router)
app.include_router(students.router)
app.include_router(token.router)
app.include_router(users.router)
print("All API routers included.")

# --- Default and System Endpoints ---

@app.get("/", summary="Root Endpoint", tags=["System"])
async def read_root():
    """
    A simple root endpoint to confirm that the API is running and accessible.
    """
    return {"message": "Welcome to the Undergraduate Clearance System API. See /docs for details."}

@app.get("/health", summary="Health Check", tags=["System"])
async def health_check():
    """
    Provides a health status check for the API, useful for monitoring and uptime checks.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": app.version,
    }
    return JSONResponse(status_code=200, content=health_status)

# This block allows the script to be run directly using `python main.py`
# It will start the Uvicorn server, which is ideal for development.
if __name__ == "__main__":
    print("Starting Uvicorn server for development...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

