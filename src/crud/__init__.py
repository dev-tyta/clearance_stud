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
    get_student_by_student_id,
    get_student_by_tag_id,
    update_student_tag_id,
    delete_student,
)
from .users import (
    create_user,
    get_user_by_username,
    get_user_by_tag_id,
    update_user_tag_id,
    get_user_by_id,
    delete_user,
    hash_password,  # Import hash_password from users module
    get_all_users
)
from .devices import (
    get_device_by_id_str,
    get_device_by_api_key,
    create_device_log,
    update_device_last_seen,
    delete_device,
)
from .clearance import (
    get_clearance_statuses_by_student_id,
    update_clearance_status,
    delete_clearance_status,
    get_all_clearance_status,
    get_student_clearance_status
)
from .tag_linking import (
    create_pending_tag_link,
    get_pending_link_by_id,
    delete_pending_link_by_device_id,
    get_pending_links,
)

# Export all functions
__all__ = [
    # Users
    'create_user',
    'get_user_by_username',
    'get_user_by_tag_id',
    'update_user_tag_id',
    'get_user_by_id',
    'delete_user',
    'hash_password',
    'get_all_users',
    # Students
    'create_student',
    'get_all_students',
    'get_student_by_student_id',
    'get_student_by_tag_id',
    'update_student_tag_id',
    'delete_student',
    # Devices
    'get_device_by_id_str',
    'get_device_by_api_key',
    'create_device_log',
    'update_device_last_seen',
    'delete_device',
    # Clearance
    'get_clearance_statuses_by_student_id',
    'update_clearance_status',
    'delete_clearance_status',
    # Tag Linking
    'create_pending_tag_link',
    'get_pending_link_by_device_id',
    'get_pending_link_by_token',
    'delete_pending_link_by_id',
    'get_all_pending_links',
]
