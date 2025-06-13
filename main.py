from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware # Keep if CORS is needed
import uvicorn
from contextlib import asynccontextmanager


from src.database import create_db_tables, get_db 
from src.routers import students, devices, clearance, token, users, admin

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Handles application startup and shutdown events."""
    print("Application startup...")
    create_db_tables()
    print("Database tables checked/created.")
    yield
    print("Application shutdown...")


# FastAPI app instance
app = FastAPI(
    title="Undergraduate Clearance System API",
    description="""
    A comprehensive API for managing student clearance processes with RFID authentication.
    
    ## Features
    * RFID Authentication - Students and staff use RFID tags for quick access
    * Multi-Department Clearance - Support for Library, Bursary, Alumni, and Departmental clearances
    * Device Management - ESP32 RFID readers with secure API key authentication
    * Role-Based Access - Different permissions for Students, Staff, and Administrators
    * Real-Time Tracking - Live clearance status updates and comprehensive logging
    
    ## Authentication Methods
    * JWT Tokens - For web interface and administrative access
    * RFID Tags - For quick student and staff authentication
    * Device API Keys - For ESP32 RFID reader authentication
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins= ['*'],
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# Include routers
app.include_router(devices.router)
app.include_router(students.router)
app.include_router(clearance.router)
app.include_router(token.router)
app.include_router(users.router)
app.include_router(admin.router)

# Root endpoint
@app.get("/", summary="Root endpoint", tags=["Default"])
async def read_root():
    """Basic root endpoint to confirm the API is running."""
    return {"message": "Undergraduate Clearance System API is running"}


@app.get("/version", summary="API Version Information", tags=["System"])
async def get_version():
    """Get detailed API version information."""
    return {
        "api_version": "2.0.0",
        "last_updated": "2025-06-07",
        "features": [
            "RFID Authentication",
            "Multi-Department Clearance",
            "Device Management",
            "Real-Time Tracking",
            "Comprehensive Logging"
        ],
        "supported_authentication": [
            "JWT Tokens",
            "RFID Tags",
            "Device API Keys"
        ]
    }

# Health check endpoints
@app.get("/health", summary="Health Check", tags=["System"])
async def health_check():
    """Comprehensive health check endpoint."""
    health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "uptime": "calculated_if_needed"
        }
        
    status_code = 200
    return JSONResponse(
            status_code=status_code,
            content=health_status
        )
    
# Run the FastAPI app using Uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
