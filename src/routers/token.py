from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from datetime import timedelta

from src.database import get_session
from src.auth import authenticate_user, create_access_token
from src.models import Token
from src.config import settings

router = APIRouter(tags=["Authentication"])

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_session)
):
    """
    Provides a JWT access token for a valid user (student or staff).
    
    This is the primary login endpoint. It uses the standard OAuth2
    password flow. The client sends 'username' and 'password' in a
    form-data body.
    """
    # The authenticate_user function will check both Student and User tables
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Create the JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
