from pydantic_settings import BaseSettings
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    POSTGRES_URI: str = os.getenv("POSTGRES_URI", "postgresql://user:password@localhost/dbname")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_secret_key")
    SECRET_KEY: str = JWT_SECRET_KEY  # ADD THIS - referenced in auth.py
    ALGORITHM: str = "HS256"  # ADD THIS - referenced in auth.py
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ADD THIS - referenced in auth.py
    PWD_CONTEXT: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    class Config:
        env_file = ".env"

settings = Settings()