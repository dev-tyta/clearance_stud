from fastapi import HTTPException, status, Header, Depends
from src.database import database, devices
# from src.models import Device  # If you have a Pydantic model for a device row

# Dependency to get and verify API key from header
async def get_verified_device(x_api_key: str = Header(..., description="The API Key for the ESP32 device.")):
    """
    Verifies if the provided API key in the 'X-API-KEY' header is valid.
    Returns the device record if valid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in X-API-KEY header",
        )
    
    query = devices.select().where(devices.c.api_key == x_api_key)
    device_row = await database.fetch_one(query)

    if not device_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    # Optionally convert to a Pydantic model:
    # return Device(**device_row)
    return device_row # Returns the raw database row (dictionary-like)
