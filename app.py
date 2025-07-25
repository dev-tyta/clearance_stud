import streamlit as st
import requests
from typing import List, Dict, Optional, Any
import pandas as pd
import time

# --- Configuration ---
API_BASE_URL = "https://testys-clearance-sys.hf.space"  # Replace with your deployed backend URL

# --- API Client ---
class APIClient:
    """A client to interact with the FastAPI backend."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        # Always use the latest token from session state if it exists
        if "token" in st.session_state and st.session_state.token:
            self.headers["Authorization"] = f"Bearer {st.session_state.token}"

    def _handle_response(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        """Handles HTTP responses, showing errors in Streamlit."""
        if 200 <= response.status_code < 300:
            if response.status_code == 204: # No Content
                return {"status": "success"}
            return response.json()
        else:
            try:
                error_data = response.json()
                detail = error_data.get("detail", "Unknown error")
                # Don't show auth errors on every check, only on explicit actions
                if response.status_code not in [401, 403]:
                    st.error(f"API Error ({response.status_code}): {detail}")
            except requests.exceptions.JSONDecodeError:
                 if response.status_code not in [401, 403]:
                    st.error(f"API Error ({response.status_code}): {response.text}")
            return None

    def login(self, username, password) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/token"
        data = {"username": username, "password": password}
        response = requests.post(url, data=data) # Form data for token endpoint
        # Handle login response separately to show specific errors
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Login failed. Please check your username and password.")
            return None

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/users/me"
        # Ensure headers are updated for this specific call
        if "token" in st.session_state and st.session_state.token:
            self.headers["Authorization"] = f"Bearer {st.session_state.token}"
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        return None

    def get_all_students(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/admin/students/"
        response = requests.get(url, headers=self.headers)
        data = self._handle_response(response)
        return data if data else []

    def create_student(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/admin/students/"
        response = requests.post(url, json=data, headers=self.headers)
        return self._handle_response(response)
    
    def lookup_student(self, matric_no: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/admin/students/lookup?matric_no={matric_no}"
        response = requests.get(url, headers=self.headers)
        return self._handle_response(response)

    def update_clearance(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/clearance/"
        response = requests.put(url, json=data, headers=self.headers)
        return self._handle_response(response)

    def link_tag(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/admin/tags/link"
        response = requests.post(url, json=data, headers=self.headers)
        return self._handle_response(response)

    def unlink_tag(self, tag_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/admin/tags/{tag_id}/unlink"
        response = requests.delete(url, headers=self.headers)
        return self._handle_response(response)
        
    def get_all_devices(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/admin/devices/"
        response = requests.get(url, headers=self.headers)
        data = self._handle_response(response)
        return data if data else []

    def create_device(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/admin/devices/"
        response = requests.post(url, json=data, headers=self.headers)
        return self._handle_response(response)

    def activate_scanner(self, device_id: int) -> bool:
        url = f"{self.base_url}/admin/scanners/activate"
        response = requests.post(url, json={"device_id": device_id}, headers=self.headers)
        if not (200 <= response.status_code < 300):
            self._handle_response(response) # Show error
        return response.status_code == 204

    def retrieve_scanned_tag(self) -> Optional[str]:
        url = f"{self.base_url}/admin/scanners/retrieve"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 404: # It's okay if no tag is found yet
            return None
        data = self._handle_response(response)
        return data.get("tag_id") if data else None

# --- Main App ---

st.set_page_config(page_title="Clearance System Dashboard", layout="wide")

# Initialize API client. Re-initialized on each run to get latest token.
client = APIClient(API_BASE_URL)

def show_login_page():
    st.title("Admin & Staff Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            response = client.login(username, password)
            if response and "access_token" in response:
                st.session_state.token = response["access_token"]
                st.session_state.user = None # Force re-fetch of user
                st.rerun()

def display_student_dashboard():
    st.header("Student Clearance Management")
    
    st.subheader("Update Student Clearance")
    
    matric_no_input = st.text_input("Enter Matriculation Number to find a student", key="lookup_matric")
    if matric_no_input:
        student = client.lookup_student(matric_no_input)
        st.session_state.selected_student = student # Store result, even if None
                
    if 'selected_student' in st.session_state and st.session_state.selected_student:
        student = st.session_state.selected_student
        st.success(f"Found Student: **{student['full_name']}** (Matric: {student['matric_no']})")

        statuses = student.get('clearance_statuses', [])
        if statuses:
            df = pd.DataFrame(statuses)
            st.write("Current Clearance Status:")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No clearance records found for this student.")
        
        with st.form("clearance_update_form"):
            st.write("Select department to update:")
            departments = [s['department'] for s in statuses] if statuses else []
            if not departments:
                 st.warning("Cannot update status as no clearance departments are listed.")
                 st.form_submit_button("Update Status", disabled=True)
            else:
                dept_to_update = st.selectbox("Department", options=departments)
                new_status = st.selectbox("New Status", options=["approved", "rejected", "pending"])
                remarks = st.text_area("Remarks (Optional)")
                
                submitted = st.form_submit_button("Update Status")
                if submitted:
                    update_data = {
                        "matric_no": student['matric_no'],
                        "department": dept_to_update,
                        "status": new_status,
                        "remarks": remarks
                    }
                    result = client.update_clearance(update_data)
                    if result:
                        st.success(f"Successfully updated {dept_to_update} to {new_status}.")
                        st.session_state.selected_student = client.lookup_student(student['matric_no'])
                        st.rerun()

def display_rfid_dashboard():
    st.header("RFID Tag Management")
    
    # Initialize session state for the scanning workflow
    if 'scan_active' not in st.session_state:
        st.session_state.scan_active = False

    devices = client.get_all_devices()
    if not devices:
        st.warning("No RFID scanners registered. Please add one in the Device Management panel.")
        return

    device_options = {f"{d['device_name']} ({d['location']})": d['id'] for d in devices}
    selected_device_name = st.selectbox("Select your desk scanner", options=device_options.keys())
    
    st.subheader("Link Tag to Student")

    # This block shows the UI when the scanner is armed and waiting for a card tap.
    if st.session_state.scan_active:
        st.info("Scanner is active. Please tap a card on the selected device now.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Fetch Scanned Card"):
                tag_id = client.retrieve_scanned_tag()
                if tag_id:
                    st.session_state.scanned_tag_id = tag_id
                    st.session_state.scan_active = False  # Deactivate after successful fetch
                    st.success(f"Card Scanned! Tag ID: `{tag_id}`")
                    st.rerun()
                else:
                    st.warning("No card has been scanned yet. Please tap a card on the device and try again.")
        with col2:
            if st.button("Cancel Scan"):
                st.session_state.scan_active = False
                st.rerun()
    # This block shows the default UI to start the process.
    else:
        if st.button("Activate Scanner for Next Scan"):
            device_id = device_options[selected_device_name]
            if client.activate_scanner(device_id):
                st.session_state.scan_active = True
                st.rerun()  # Rerun to show the "active" state UI
        
    # This block appears after a tag has been successfully scanned and retrieved.
    if 'scanned_tag_id' in st.session_state:
        tag_id = st.session_state.scanned_tag_id
        st.info(f"Ready to link Tag ID: `{tag_id}`")

        with st.form("link_tag_form"):
            matric_to_link = st.text_input("Enter Matriculation Number to link this tag to")
            submitted = st.form_submit_button("Link Tag")

            if submitted and matric_to_link:
                link_data = {"tag_id": tag_id, "matric_no": matric_to_link}
                result = client.link_tag(link_data)
                if result:
                    st.success(f"Successfully linked tag {tag_id} to {matric_to_link}.")
                    del st.session_state.scanned_tag_id
                    st.rerun()
        
    st.subheader("Unlink a Tag")
    with st.form("unlink_tag_form"):
        tag_to_unlink = st.text_input("Enter Tag ID to unlink")
        submitted = st.form_submit_button("Unlink Tag")
        if submitted and tag_to_unlink:
            result = client.unlink_tag(tag_to_unlink)
            if result:
                st.success(f"Successfully unlinked tag {tag_to_unlink}.")

def display_super_admin_dashboard():
    st.header("Super Admin Panel")

    with st.expander("Manage Users (Admins & Staff)", expanded=False):
        # User management UI here
        st.info("User management section to be built.")

    with st.expander("Manage RFID Devices", expanded=True):
        st.subheader("Register New Device")
        with st.form("create_device_form"):
            device_name = st.text_input("Device Name (e.g., 'Library Entrance Scanner')")
            location = st.text_input("Location (e.g., 'Main Library, Ground Floor')")
            submitted = st.form_submit_button("Register Device")
            if submitted and device_name and location:
                device_data = {"device_name": device_name, "location": location}
                result = client.create_device(device_data)
                if result:
                    st.success(f"Device '{device_name}' registered successfully!")
                    st.rerun()

        st.subheader("Registered Devices")
        devices = client.get_all_devices()
        if devices:
            df_devices = pd.DataFrame(devices)
            st.dataframe(df_devices, use_container_width=True)
        else:
            st.info("No devices have been registered yet.")
            
def main():
    # This logic block now correctly handles the session state initialization
    if "token" not in st.session_state or not st.session_state.token:
        show_login_page()
        return

    # If we have a token but no user object, try to fetch it
    if "user" not in st.session_state or not st.session_state.user:
        user_details = client.get_current_user()
        if user_details:
            st.session_state.user = user_details
        else:
            # If fetching fails (e.g., token expired), clear session and re-login
            st.session_state.clear()
            show_login_page()
            return
            
    # From here, we can safely assume st.session_state.user exists
    user = st.session_state.user
    st.sidebar.title("Dashboard")
    st.sidebar.write(f"Welcome, **{user['full_name']}**")
    st.sidebar.write(f"Role: **{user['role']}**")

    # Define pages accessible by all logged-in users (Staff + Admin)
    pages = ["Student Management", "RFID Management"]
    # Only add Super Admin page if user has the correct role
    if user['role'] == 'admin':
        pages.append("Super Admin")

    page = st.sidebar.radio("Navigate", pages)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
        
    # --- Page Routing ---
    if page == "Student Management":
        display_student_dashboard()
    elif page == "RFID Management":
        display_rfid_dashboard()
    elif page == "Super Admin":
        # Second check to be absolutely sure
        if user['role'] == 'admin':
            display_super_admin_dashboard()
        else:
            st.error("You are not authorized to view this page.")

if __name__ == "__main__":
    main()
