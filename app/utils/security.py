import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_secure_filename(original_filename: str) -> str:
    """Generate secure filename with random string"""
    # Get file extension
    if "." in original_filename:
        name, ext = original_filename.rsplit(".", 1)
        ext = ext.lower()
    else:
        name = original_filename
        ext = ""

    # Generate random string
    random_string = "".join(
        secrets.choice(string.ascii_lowercase + string.digits) for _ in range(16)
    )

    # Combine with timestamp
    timestamp = int(datetime.utcnow().timestamp())

    if ext:
        return f"{timestamp}_{random_string}.{ext}"
    else:
        return f"{timestamp}_{random_string}"


def generate_video_token(video_id: int, user_id: int) -> str:
    """Generate secure token for video streaming"""
    data = {
        "video_id": video_id,
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1),  # Token expires in 1 hour
    }
    return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)


def verify_video_token(token: str) -> dict:
    """Verify video streaming token"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid video token"
        )
