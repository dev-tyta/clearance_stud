import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from main import app, get_session

# --- Test Database Setup ---

# Define the connection string for a test database. 
# Using SQLite in-memory is fast and simple for testing.
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def override_get_session():
    """Dependency override to use the test database session."""
    with Session(engine) as session:
        yield session


# This line tells our app to use the test database for tests
app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(scope="function", name="db")
def get_db_session():
    """
    Pytest fixture to create a fresh database for each test function.
    """
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="module", name="client")
def get_test_client():
    """
    Pytest fixture to provide a TestClient for making API requests.
    """
    with TestClient(app) as client:
        yield client
