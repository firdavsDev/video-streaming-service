import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.security import verify_password, verify_token

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        try:
            user = self.db.query(User).filter(User.username == username).first()

            if not user:
                logger.warning(f"Authentication failed: User '{username}' not found")
                return None

            if not user.is_active:
                logger.warning(f"Authentication failed: User '{username}' is inactive")
                return None

            if not verify_password(password, user.hashed_password):
                logger.warning(
                    f"Authentication failed: Invalid password for user '{username}'"
                )
                return None

            logger.info(f"User '{username}' authenticated successfully")
            return user

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None


# Dependency to get current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user"""

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token
    payload = verify_token(credentials.credentials)
    username: str = payload.get("sub")

    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    auth_service = AuthService(db)
    user = auth_service.get_user_by_username(username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# Dependency to get current admin user
async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated admin user"""

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return current_user


# Optional authentication (for public endpoints that can benefit from user context)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""

    if not credentials:
        return None

    try:
        payload = verify_token(credentials.credentials)
        username: str = payload.get("sub")

        if username is None:
            return None

        auth_service = AuthService(db)
        user = auth_service.get_user_by_username(username)

        if user and user.is_active:
            return user

    except HTTPException:
        pass  # Invalid token, return None

    return None
