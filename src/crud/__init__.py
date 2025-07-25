"""
CRUD Package Initializer

This file makes the 'crud' directory a Python package and imports all the
public CRUD functions from the submodules. This allows you to import any
CRUD function directly from `src.crud` instead of the specific submodule,
keeping the router imports clean.
"""

from .students import (
    create_student,
    get_all_students,
    get_student_by_id,  # FIX: was get_student_by_student_id
    get_student_by_matric_no,  # ADD: missing import
    get_student_by_tag_id,
    update_student,  # FIX: was update_student_tag_id
    delete_student,
)
from .users import (
    create_user,
    get_user_by_username,
    get_user_by_tag_id,
    get_user_by_id,
    update_user,  # FIX: was update_user_tag_id
    delete_user,
    hash_password,
    get_all_users
)
from .devices import (
    create_device,  # ADD: missing
    get_device_by_api_key,
    get_device_by_location,  # ADD: missing
    get_all_devices,  # ADD: missing
    delete_device,
)
from .clearance import (
    update_clearance_status,
    is_student_fully_cleared,  # ADD: missing
)
from .tag_linking import (
    link_tag,
    unlink_tag,
)

# Export all functions
__all__ = [
    # Users
    'create_user',
    'get_user_by_username',
    'get_user_by_tag_id',
    'get_user_by_id',
    'update_user',
    'delete_user',
    'hash_password',
    'get_all_users',
    # Students
    'create_student',
    'get_all_students',
    'get_student_by_id',
    'get_student_by_matric_no',
    'get_student_by_tag_id',
    'update_student',
    'delete_student',
    # Devices
    'create_device',
    'get_device_by_api_key',
    'get_device_by_location',
    'get_all_devices',
    'delete_device',
    # Clearance
    'update_clearance_status',
    'is_student_fully_cleared',
    # Tag Linking
    'link_tag',
    'unlink_tag',
]
