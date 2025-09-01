from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
import os
from .models import User
from .schemas import TokenData
import logging

logger = logging.getLogger(__name__)

# Get JWT secret from environment or settings (no network calls at import time)
SECRET_KEY = os.getenv("SECRET_KEY") or settings.secret_key
# Optional secondary key to support seamless rotation or mixed-instance deployments
SECONDARY_SECRET_KEY = os.getenv("SECONDARY_SECRET_KEY")

ALGORITHM = settings.algorithm

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Try validate with primary key, then optional secondary key (for rotation safety)
        payload = None
        last_error: Optional[Exception] = None
        for key in [SECRET_KEY, SECONDARY_SECRET_KEY]:
            if not key:
                continue
            try:
                payload = jwt.decode(token, key, algorithms=[ALGORITHM])
                break
            except JWTError as e:
                last_error = e
                continue
        if payload is None:
            # Log at debug level without leaking token
            logger.debug("JWT validation failed with both primary and secondary keys: %s", last_error)
            raise credentials_exception
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_company_manager(current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["admin", "company_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company manager access required"
        )
    return current_user
