import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import Token, User, UserLogin
from app.services.auth_service import (
    AuthService,
    get_current_admin_user,
    get_current_user,
)
from app.utils.security import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Admin login endpoint"""

    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin},
        expires_delta=access_token_expires,
    )

    logger.info(f"Admin user '{user.username}' logged in successfully")

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=User.from_orm(user),
    )


@router.post("/login-json", response_model=Token)
async def login_json(login_data: UserLogin, db: Session = Depends(get_db)):
    """Admin login with JSON payload"""

    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin},
        expires_delta=access_token_expires,
    )

    logger.info(f"Admin user '{user.username}' logged in successfully")

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=User.from_orm(user),
    )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/verify-admin")
async def verify_admin_access(current_admin: User = Depends(get_current_admin_user)):
    """Verify admin access"""
    return {
        "message": "Admin access verified",
        "user": {
            "id": current_admin.id,
            "username": current_admin.username,
            "email": current_admin.email,
        },
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint (client-side token removal)"""
    logger.info(f"User '{current_user.username}' logged out")
    return {"message": "Successfully logged out"}
