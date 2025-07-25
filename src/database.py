from sqlmodel import create_engine, Session, SQLModel
from src.config import settings

# --- Database Engine Setup ---

# The database URL is constructed from the application settings.
# This makes it easy to switch between different database environments (e.g., dev, test, prod).
DATABASE_URL = settings.POSTGRES_URI
engine = create_engine(DATABASE_URL, echo=True) # echo=True logs SQL queries, useful for debugging

# --- Database Initialization ---

def create_db_and_tables():
    """
    Creates all database tables defined by SQLModel metadata.
    This function is called once at application startup.
    """
    print("Initializing database...")
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully (if they didn't exist).")

# --- Database Session Management ---

def get_session():
    """
    A FastAPI dependency that provides a database session for each request.
    It ensures that the session is always closed after the request is finished,
    even if an error occurs.
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()

