"""
Utility functions for CRUD operations.
"""
import bcrypt

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password_str: str) -> bool:
    """Verifies a plain password against a hashed password."""
    if not plain_password or not hashed_password_str:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_str.encode('utf-8'))