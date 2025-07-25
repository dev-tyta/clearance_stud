import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app  # Assuming your FastAPI app instance is in main.py
from src.models import Role, User, Student, Department, ClearanceStatus

# TestClient allows us to make requests to our app in tests
client = TestClient(app)

# --- Test Data ---
SUPER_ADMIN_USER = {"username": "testadmin", "password": "a_very_secure_password", "role": Role.ADMIN}
STAFF_USER = {"username": "teststaff", "password": "a_secure_password", "role": Role.STAFF}
STUDENT_USER = {"username": "teststudent", "password": "a_password", "role": Role.STUDENT} # This user will be used to test unauthorized access

NEW_STUDENT_DATA = {
    "full_name": "Adewale Johnson",
    "matric_no": "F/HD/21/999999",
    "department": Department.COMPUTER_SCIENCE
}
UNLINKED_TAG_ID = "1122334455"


# Helper function to get an authentication token
def get_auth_token(username, password):
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200, f"Failed to get token for {username}"
    return response.json()["access_token"]


# --- Test Suite for Admin Router ---

def test_create_initial_users_for_auth(db: Session):
    """
    This isn't a real test, but a setup step to ensure our auth users exist in the test DB.
    Pytest will run this automatically because it uses the 'db' fixture.
    """
    # Using a try/except block to prevent errors if users already exist from a previous test run
    try:
        client.post("/admin/users/", json=SUPER_ADMIN_USER, headers={"Authorization": f"Bearer {get_auth_token('initial_admin', 'admin_password')}"})
    except: # This will fail if the initial_admin doesn't exist, which is fine for the first run
        pass 
        
    # Create the users needed for our tests
    admin_token = get_auth_token(SUPER_ADMIN_USER["username"], SUPER_ADMIN_USER["password"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/admin/users/", json=STAFF_USER, headers=headers)
    
    # We create the student user via the student creation endpoint
    # This is a more realistic scenario.
    client.post("/admin/students/", json={**STUDENT_USER, **NEW_STUDENT_DATA}, headers=headers)


def test_create_student_as_admin_and_staff():
    """Tests that both Admins and Staff can create students."""
    # Test with Admin token
    admin_token = get_auth_token(SUPER_ADMIN_USER["username"], SUPER_ADMIN_USER["password"])
    response = client.post("/admin/students/", json=NEW_STUDENT_DATA, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 201
    assert response.json()["matric_no"] == NEW_STUDENT_DATA["matric_no"]
    assert len(response.json()["clearance_statuses"]) > 0 # Check that statuses were created

    # Test with Staff token
    staff_token = get_auth_token(STAFF_USER["username"], STAFF_USER["password"])
    # Use a different matric no to avoid conflict
    student_data_2 = {**NEW_STUDENT_DATA, "matric_no": "F/HD/21/888888"}
    response = client.post("/admin/students/", json=student_data_2, headers={"Authorization": f"Bearer {staff_token}"})
    assert response.status_code == 201


def test_create_student_unauthorized():
    """Ensures a student cannot access the create student endpoint."""
    student_token = get_auth_token(STUDENT_USER["username"], STUDENT_USER["password"])
    response = client.post("/admin/students/", json=NEW_STUDENT_DATA, headers={"Authorization": f"Bearer {student_token}"})
    assert response.status_code == 403 # 403 Forbidden


def test_link_and_unlink_tag_as_admin():
    """Tests the full lifecycle of linking and unlinking a tag."""
    admin_token = get_auth_token(SUPER_ADMIN_USER["username"], SUPER_ADMIN_USER["password"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Link the tag
    link_data = {"matric_no": NEW_STUDENT_DATA["matric_no"], "tag_id": UNLINKED_TAG_ID}
    response = client.post("/admin/tags/link", json=link_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["tag_id"] == UNLINKED_TAG_ID

    # 2. Try to link the same tag again (should fail)
    response = client.post("/admin/tags/link", json=link_data, headers=headers)
    assert response.status_code == 409 # 409 Conflict

    # 3. Unlink the tag
    response = client.delete(f"/admin/tags/{UNLINKED_TAG_ID}/unlink", headers=headers)
    assert response.status_code == 200
    assert response.json()["tag_id"] == UNLINKED_TAG_ID
    
    # 4. Try to unlink it again (should fail)
    response = client.delete(f"/admin/tags/{UNLINKED_TAG_ID}/unlink", headers=headers)
    assert response.status_code == 404 # 404 Not Found


def test_user_creation_permissions():
    """Ensures only a Super Admin can create other users."""
    admin_token = get_auth_token(SUPER_ADMIN_USER["username"], SUPER_ADMIN_USER["password"])
    staff_token = get_auth_token(STAFF_USER["username"], STAFF_USER["password"])

    # Attempt to create a user as Staff (should be forbidden)
    new_user_data = {"username": "anotherstaff", "password": "password", "role": Role.STAFF}
    response = client.post("/admin/users/", json=new_user_data, headers={"Authorization": f"Bearer {staff_token}"})
    assert response.status_code == 403 # Forbidden

    # Create user as Super Admin (should succeed)
    response = client.post("/admin/users/", json=new_user_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 201
    assert response.json()["username"] == "anotherstaff"

