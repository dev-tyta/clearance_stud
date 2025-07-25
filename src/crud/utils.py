"""
Utility functions for CRUD operations.
"""
from src.config import settings

# --- Password Hashing ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return settings.PWD_CONTEXT.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return settings.PWD_CONTEXT.hash(password)