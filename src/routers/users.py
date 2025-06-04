from fastapi import APIRouter, Depends, HTTPException, status
from src import crud
from src.models import UserCreate, UserResponse, TagLinkRequest # Added TagLinkRequest
from src.auth import get_current_active_admin_user_from_token

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(get_current_active_admin_user_from_token)] # Protect all routes in this router
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new staff or admin user (Admin Only)")
async def register_user(
    user_data: UserCreate, 
    # current_admin: dict = Depends(get_current_active_admin_user_from_token) # Dependency already at router level
):
    """
    Registers a new staff or admin user. 
    This endpoint is only accessible by an authenticated admin user.
    """
    existing_user = await crud.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Ensure role is either staff or admin if creating through this endpoint
    if user_data.role not in ["staff", "admin"]:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User role must be 'staff' or 'admin'"
        )

    created_user = await crud.create_user(user_data)
    # crud.create_user currently returns a dict that matches UserResponse structure
    # If it didn't, we would map it here:
    # return UserResponse(**created_user) 
    return created_user

@router.put("/{username}/link-tag", response_model=UserResponse, summary="Link or update RFID tag for a staff/admin user (Admin Only)")
async def link_user_tag_endpoint(
    username: str,
    tag_link_request: TagLinkRequest,
    # current_admin: dict = Depends(get_current_active_admin_user_from_token) # Dependency already at router level
):
    """
    Links or updates the RFID tag_id for a specific staff or admin user.
    If the user already has a tag, it will be overwritten.
    The new tag_id must be unique across all students and users.
    Accessible only by authenticated admin users (due to router-level dependency).
    """
    try:
        updated_user = await crud.update_user_tag_id(username, tag_link_request.tag_id)
        # crud.update_user_tag_id raises HTTPException on errors like not found or tag conflict
        return updated_user
    except HTTPException as e:
        raise e
    except Exception as e:
        # Log error e
        # print(f"Unexpected error in link_user_tag_endpoint: {e}") # Basic logging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while linking tag to user.")
