from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List # Import List for type hinting
from src.database import connect_db, disconnect_db, database # Also import database instance if needed directly in main
from src.models import (
    StudentCreate, Student, ClearanceStatusCreate,
    ClearanceStatus, ClearanceDetail, DeviceRegister,
    DeviceResponse, TagScan
) # Pydantic models
from src import crud # Database operations (now uses databases)
from src.auth import verify_api_key # API key verification dependency (now uses databases)
# Import routers
from src.routers import students, devices, clearance # Assuming you create these



# FastAPI app instance
app = FastAPI(title="Undergraduate Clearance System API", version="1.0.0")

# Enable CORS (Cross-Origin Resource Sharing)
# This allows your frontend (running on a different origin) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WARNING: Use specific origins in production (e.g., ["http://localhost:3000", "https://your-frontend-domain.com"])
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# --- Database Connection Lifecycle ---

# Connect to the database when the application starts up
@app.on_event("startup")
async def startup_event():
    await connect_db()

# Disconnect from the database when the application shuts down
@app.on_event("shutdown")
async def shutdown_event():
    await disconnect_db()

# Include routers
app.include_router(devices.router)
app.include_router(students.router)
app.include_router(clearance.router)

# --- Root Endpoint (Optional) ---
@app.get("/", summary="Root endpoint")
async def read_root():
    """Basic root endpoint to confirm the API is running."""
    return {"message": "Undergraduate Clearance System API is running"}

# --- Run the FastAPI app ---
if __name__ == "__main__":
    # Use uvicorn to run the FastAPI application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
