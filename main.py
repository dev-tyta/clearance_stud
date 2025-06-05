from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Keep if CORS is needed
import uvicorn
from contextlib import asynccontextmanager

# Import create_db_tables from database.py
from src.database import create_db_tables, get_db # get_db might not be used directly here but good to be aware of
# Routers
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
    title="Undergraduate Clearance System API (ORM)",
    description="API for managing student clearance and RFID interactions.",
    version="1.1.0", # Incremented version
    lifespan=lifespan
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

# Run the FastAPI app using Uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
