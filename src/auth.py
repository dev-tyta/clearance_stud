from fastapi import HTTPException, status, Depends
from src.database import database, devices # Import database instance and devices table

# Dependency to verify the API key sent by ESP32 devices
async def verify_api_key(api_key: str = Depends(HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key"))):
    """
    Verifies if the provided API key is valid and corresponds to a registered device
    using the 'databases' library.

    Args:
        api_key: The API key provided in the request header or body.

    Returns:
        The database record of the device if the API key is valid.

    Raises:
        HTTPException: If the API key is invalid or not found.
    """
    # Use 'databases' to execute a select query on the 'devices' table
    query = devices.select().where(devices.c.api_key == api_key)
    device = await database.fetch_one(query) # fetch_one returns a single record or None

    if not device:
        # Raise HTTPException if the API key is not found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}, # Optional: Suggest Bearer token scheme
        )
    return device
