import streamlit as st
import requests
import pandas as pd
from typing import Dict, Any, Optional, List

# --- Configuration ---
# IMPORTANT: Change this URL to your hosted backend's URL if it's not running locally.
API_BASE_URL = "https://testys-clearance-sys.hf.space/api"

# --- Page Setup ---
st.set_page_config(
    page_title="Clearance System",
    page_icon="✅",
    layout="wide",
)

# --- Helper Functions ---
def api_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    x_api_key: Optional[str] = None,
    x_user_tag_id: Optional[str] = None,
) -> requests.Response:
    """A centralized function to make HTTP requests to the FastAPI backend."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if x_api_key:
        headers["X-API-KEY"] = x_api_key
    if x_user_tag_id:
        headers["X-User-Tag-ID"] = x_user_tag_id

    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, params=params, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, params=params, timeout=10)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None
        return response
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error: Could not connect to the API at {url}. Please ensure the backend is running and accessible.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def handle_api_response(response: Optional[requests.Response], success_status_code: int = 200, display_success_json=True):
    """Displays success or error messages based on API response."""
    if response and response.status_code == success_status_code:
        st.success("Operation successful!")
        if display_success_json:
            try:
                if response.text:
                    st.json(response.json())
                else:
                    st.info("Request successful with no content returned.")
            except requests.exceptions.JSONDecodeError:
                st.code(response.text)
    elif response:
        st.error(f"Error: {response.status_code}")
        try:
            st.json(response.json())
        except requests.exceptions.JSONDecodeError:
            st.code(response.text)
    else:
        # Error from connection issues is already displayed by api_request
        pass


# --- Initialize session state variables ---
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "device_api_key" not in st.session_state:
    st.session_state.device_api_key = ""
if "tag_id_for_header" not in st.session_state:
    st.session_state.tag_id_for_header = ""


# --- Page Definitions ---

def login_page():
    st.header("👤 User Login (Staff/Admin)")
    st.markdown("Log in to get a JWT token for accessing protected admin endpoints.")

    if st.session_state.access_token and st.session_state.user_info:
        user = st.session_state.user_info
        role_display = user.get('role')
        if isinstance(role_display, dict):
            role_display = role_display.get('value', 'N/A')
        st.success(f"Logged in as **{user.get('username')}** (Role: **{role_display}**)")
        if st.button("Logout"):
            st.session_state.access_token = None
            st.session_state.user_info = None
            st.rerun()
        return

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Username and password are required.")
                return
            form_data_payload = {'username': username, 'password': password}
            try:
                login_response = requests.post(f"{API_BASE_URL}/token/login", data=form_data_payload)
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    st.session_state.access_token = token_data.get("access_token")
                    user_me_response = api_request("GET", "/users/users/me", token=st.session_state.access_token)
                    if user_me_response and user_me_response.status_code == 200:
                        st.session_state.user_info = user_me_response.json()
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(f"Failed to fetch user details: {user_me_response.text if user_me_response else 'No response'}")
                        st.session_state.access_token = None
                else:
                    st.error(f"Login failed: {login_response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"An error occurred during login: {e}")


def admin_management_page():
    st.header("👑 Admin Panel")
    if not st.session_state.access_token or not st.session_state.user_info:
        st.warning("Please log in as an Admin to access this page.")
        return

    user_role = st.session_state.user_info.get('role')
    actual_role_value = user_role if isinstance(user_role, str) else (user_role.get('value') if isinstance(user_role, dict) else None)
    if actual_role_value != 'admin':
        st.warning("Access Denied. You must be an Admin.")
        return

    token = st.session_state.access_token
    admin_tabs = st.tabs([
        "Manage Users", "Manage Students", "Manage Devices", 
        "View All Users", "View All Students", "View All Devices"
    ])

    with admin_tabs[0]: # Manage Users
        st.subheader("Register New Staff/Admin User")
        with st.form("register_user_form", clear_on_submit=True):
            cols = st.columns(2)
            user_data = {
                "username": cols[0].text_input("Username"),
                "password": cols[1].text_input("Password", type="password"),
                "role": cols[0].selectbox("Role", ["STAFF", "ADMIN"]),
                "department": cols[1].selectbox("Department", ["DEPARTMENTAL", "LIBRARY", "BURSARY", "ALUMNI"], index=None, placeholder="Select department (for Staff)"),
                "tag_id": cols[0].text_input("Tag ID (Optional)"),
                "is_active": True
            }
            if st.form_submit_button("Register User", use_container_width=True):
                user_data["tag_id"] = user_data["tag_id"] or None
                response = api_request("POST", "/users/register", data=user_data, token=token)
                handle_api_response(response, 201)

    with admin_tabs[1]: # Manage Students
        st.subheader("Create New Student")
        with st.form("create_student_form", clear_on_submit=True):
            cols = st.columns(2)
            student_data = {
                "student_id": cols[0].text_input("Student ID (Matric No.)"),
                "name": cols[1].text_input("Full Name"),
                "email": cols[0].text_input("Email"),
                "department": cols[1].text_input("Department (e.g., Computer Science)"),
                "tag_id": cols[0].text_input("Tag ID (Optional)")
            }
            if st.form_submit_button("Create Student", use_container_width=True):
                student_data["tag_id"] = student_data["tag_id"] or None
                response = api_request("POST", "/students/", data=student_data, token=token)
                handle_api_response(response, 201)

        st.subheader("Get Specific Student's Clearance")
        with st.form("get_student_clearance_form"):
            stud_id_to_view = st.text_input("Enter Student ID to View Clearance")
            if st.form_submit_button("Fetch Clearance", use_container_width=True):
                 response = api_request("GET", f"/students/{stud_id_to_view}", token=token)
                 handle_api_response(response)

    with admin_tabs[2]: # Manage Devices
        st.subheader("Register New Device")
        with st.form("admin_register_device_form", clear_on_submit=True):
            device_data = {
                "name": st.text_input("Device Name (e.g., Library Scanner 1)"),
                "location": st.text_input("Device Location"),
                "device_id": st.text_input("Device Hardware ID (Optional)"),
                "description": st.text_area("Description")
            }
            if st.form_submit_button("Register Device", use_container_width=True):
                device_data["device_id"] = device_data["device_id"] or None
                response = api_request("POST", "/admin/devices/", data=device_data, token=token)
                handle_api_response(response, 201)
        
        st.subheader("Prepare Device for Tag Linking")
        with st.form("prepare_tag_link_form", clear_on_submit=True):
            prepare_data = {
                "device_identifier": st.text_input("Device Identifier (Hardware ID or DB PK)"),
                "target_user_type": st.selectbox("Target User Type", ["STUDENT", "STAFF_ADMIN"]),
                "target_identifier": st.text_input("Target Identifier (Student ID or Username)")
            }
            if st.form_submit_button("Prepare Device", use_container_width=True):
                response = api_request("POST", "/admin/prepare-device-tag-link", data=prepare_data, token=token)
                handle_api_response(response, 202)

    with admin_tabs[3]: # View All Users
        st.subheader("List of All Staff/Admin Users")
        if st.button("Fetch All Users", use_container_width=True):
            response = api_request("GET", "/users/", token=token)
            if response and response.status_code == 200:
                st.success("Users retrieved successfully!")
                df = pd.DataFrame(response.json())
                st.dataframe(df.drop(columns=['hashed_password'], errors='ignore'))
            else:
                handle_api_response(response)

    with admin_tabs[4]: # View All Students
        st.subheader("List of All Students")
        if st.button("Fetch All Students", use_container_width=True):
            response = api_request("GET", "/students/", token=token)
            if response and response.status_code == 200:
                st.success("Students retrieved successfully!")
                st.dataframe(pd.DataFrame(response.json()))
            else:
                handle_api_response(response)
    
    with admin_tabs[5]: # View All Devices
        st.subheader("List of All Devices")
        if st.button("Fetch All Devices", use_container_width=True):
            response = api_request("GET", "/admin/devices/", token=token)
            if response and response.status_code == 200:
                st.success("Devices retrieved successfully!")
                st.dataframe(pd.DataFrame(response.json()))
            else:
                handle_api_response(response)

def staff_actions_page():
    st.header("👨‍🏫 Staff Actions (Tag-Based)")
    st.info("These actions simulate using a device or terminal where authentication is based on your RFID tag ID, not a login token.")
    
    tag_id = st.text_input("Your Staff Tag ID (Used for 'X-User-Tag-ID' Header)")
    if not tag_id:
        st.warning("Please enter your Staff Tag ID to proceed.")
        return

    st.subheader("Update Student Clearance")
    with st.form("update_clearance_form"):
        update_stud_id = st.text_input("Student ID to Update")
        update_dept = st.selectbox("Department", ["DEPARTMENTAL", "LIBRARY", "BURSARY", "ALUMNI"])
        update_status = st.selectbox("New Status", ["COMPLETED", "NOT_COMPLETED", "PENDING"])
        update_remarks = st.text_area("Remarks (Optional)")
        if st.form_submit_button("Update Clearance Status", use_container_width=True):
            clearance_data = { "student_id": update_stud_id, "department": update_dept, "status": update_status, "remarks": update_remarks }
            response = api_request("POST", "/clearance/", data=clearance_data, x_user_tag_id=tag_id)
            handle_api_response(response)

def student_actions_page():
    st.header("👨‍🎓 Student Actions (Tag-Based)")
    st.info("Use your student RFID tag to view your clearance status.")
    
    tag_id = st.text_input("Your Student Tag ID (Used for 'X-User-Tag-ID' Header)")
    if st.button("View My Clearance Status", use_container_width=True):
        if not tag_id:
            st.error("Please enter your Student Tag ID.")
            return
        response = api_request("GET", "/clearance/me", x_user_tag_id=tag_id)
        handle_api_response(response)

def device_simulation_page():
    st.header("📟 Device Simulation (ESP32)")
    st.info("Simulate an ESP32 device registering itself, scanning tags, and completing tag links.")

    st.subheader("1. Device Self-Registration")
    with st.form("device_self_reg_form"):
        sim_dev_hw_id = st.text_input("Device Hardware ID (e.g., 'ESP32-LIB-01')")
        sim_dev_loc = st.text_input("Device Location (e.g., 'Main Library Entrance')")
        if st.form_submit_button("Register This Device", use_container_width=True):
            response = api_request("POST", "/devices/register", data={"device_id": sim_dev_hw_id, "location": sim_dev_loc})
            if response and response.status_code == 200:
                api_key_data = response.json()
                st.session_state.device_api_key = api_key_data.get("api_key")
                st.success(f"Device '{sim_dev_hw_id}' registered. API Key received and stored in session.")
                st.code(st.session_state.device_api_key, language="text")
            else:
                handle_api_response(response)

    st.markdown("---")
    st.subheader("2. Device Actions")
    st.session_state.device_api_key = st.text_input("Device API Key (X-API-KEY)", value=st.session_state.device_api_key)
    
    if not st.session_state.device_api_key:
        st.warning("Register a device or enter an API key to perform actions.")
        return

    action_tabs = st.tabs(["Scan Student Tag", "Submit Scanned Tag (for Linking)"])
    
    with action_tabs[0]:
        st.write("Scan a student's tag to check their overall clearance status.")
        with st.form("device_scan_tag_form", clear_on_submit=True):
            scan_dev_hw_id_payload = st.text_input("Device Hardware ID (must match key's device)")
            scan_tag_id_student = st.text_input("Student Tag ID to Scan")
            if st.form_submit_button("Simulate Scan", use_container_width=True):
                scan_payload = {"device_id": scan_dev_hw_id_payload, "tag_id": scan_tag_id_student}
                response = api_request("POST", "/scan", data=scan_payload, x_api_key=st.session_state.device_api_key)
                handle_api_response(response)

    with action_tabs[1]:
        st.write("Submit a tag that has just been scanned after an admin prepared this device for linking.")
        with st.form("device_submit_scanned_tag_form", clear_on_submit=True):
            submit_scanned_tag_val = st.text_input("Tag ID Scanned by Device")
            if st.form_submit_button("Submit Scanned Tag", use_container_width=True):
                submit_payload = {"scanned_tag_id": submit_scanned_tag_val}
                response = api_request("POST", "/devices/submit-scanned-tag", data=submit_payload, x_api_key=st.session_state.device_api_key)
                handle_api_response(response)


# --- Main App Logic with Sidebar Navigation ---
st.sidebar.title("Clearance System Demo")

# Display login status
if st.session_state.access_token and st.session_state.user_info:
    user = st.session_state.user_info
    role_display = user.get('role')
    if isinstance(role_display, dict):
        role_display = role_display.get('value', 'N/A')
    st.sidebar.success(f"Logged in: **{user.get('username')}**")
    st.sidebar.caption(f"Role: {role_display}")
else:
    st.sidebar.info("Not logged in.")
st.sidebar.markdown("---")

# Navigation
page_options = {
    "🔑 Login (Staff/Admin)": login_page,
    "👑 Admin Panel": admin_management_page,
    "👨‍🏫 Staff Actions": staff_actions_page,
    "👨‍🎓 Student Actions": student_actions_page,
    "📟 Device Simulation": device_simulation_page,
}
selected_page_title = st.sidebar.radio("Navigation", list(page_options.keys()))
st.sidebar.markdown("---")
st.sidebar.info("This is a demonstration frontend for the Clearance System API.")

# Render the selected page
page_options[selected_page_title]()
