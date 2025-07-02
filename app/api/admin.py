import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.video import VideoStatus
from app.services.auth_service import AuthService, get_current_admin_user
from app.services.video_service import VideoService
from app.utils.security import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Panel"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "title": "Admin Login"}
    )


@router.post("/login")
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle admin login form submission"""

    auth_service = AuthService(db)
    user = auth_service.authenticate_user(username, password)

    if not user or not user.is_admin:
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "title": "Admin Login",
                "error": "Invalid credentials or insufficient permissions",
            },
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin},
        expires_delta=access_token_expires,
    )

    # Redirect to dashboard with token in cookie
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
    )

    logger.info(f"Admin '{user.username}' logged in successfully")
    return response


@router.get("/logout")
async def admin_logout():
    """Admin logout"""
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Admin dashboard page"""

    video_service = VideoService(db)
    stats = video_service.get_video_stats(current_admin)

    # Get recent videos
    recent_videos = video_service.get_user_videos(
        user=current_admin, page=1, per_page=5
    )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "title": "Admin Dashboard",
            "user": current_admin,
            "stats": stats,
            "recent_videos": recent_videos["items"],
        },
    )


@router.get("/upload", response_class=HTMLResponse)
async def admin_upload_page(
    request: Request, current_admin: User = Depends(get_current_admin_user)
):
    """Admin video upload page"""
    return templates.TemplateResponse(
        "admin/upload.html",
        {
            "request": request,
            "title": "Upload Video",
            "user": current_admin,
            "max_file_size": settings.max_file_size,
            "allowed_types": settings.allowed_video_types_list,
        },
    )


@router.get("/videos", response_class=HTMLResponse)
async def admin_videos_page(
    request: Request,
    page: int = 1,
    status_filter: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Admin videos management page"""

    video_service = VideoService(db)

    # Convert status filter
    status_enum = None
    if status_filter:
        try:
            status_enum = VideoStatus(status_filter)
        except ValueError:
            status_enum = None

    videos = video_service.get_user_videos(
        user=current_admin, page=page, per_page=20, status_filter=status_enum
    )

    return templates.TemplateResponse(
        "admin/videos.html",
        {
            "request": request,
            "title": "Manage Videos",
            "user": current_admin,
            "videos": videos,
            "current_page": page,
            "status_filter": status_filter,
            "video_statuses": [status.value for status in VideoStatus],
        },
    )


@router.get("/video/{video_id}", response_class=HTMLResponse)
async def admin_video_detail(
    request: Request,
    video_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Admin video detail page"""

    video_service = VideoService(db)
    video = video_service.get_video_by_id(video_id, current_admin)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    # Generate streaming token if video is completed
    streaming_token = None
    if video.status == VideoStatus.COMPLETED:
        streaming_token = video_service.generate_streaming_token(
            video_id, current_admin
        )

    return templates.TemplateResponse(
        "admin/video_detail.html",
        {
            "request": request,
            "title": f"Video: {video.title}",
            "user": current_admin,
            "video": video,
            "streaming_token": streaming_token,
            "api_base": settings.api_prefix,
        },
    )


@router.post("/video/{video_id}/delete")
async def admin_delete_video(
    video_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete video via admin panel"""

    video_service = VideoService(db)
    success = video_service.delete_video(video_id, current_admin)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or could not be deleted",
        )

    return RedirectResponse(url="/admin/videos", status_code=302)


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request, current_admin: User = Depends(get_current_admin_user)
):
    """Admin settings page"""
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "title": "Settings",
            "user": current_admin,
            "settings": {
                "max_file_size_mb": settings.max_file_size // (1024 * 1024),
                "allowed_video_types": settings.allowed_video_types_list,
                "upload_dir": settings.upload_dir,
                "video_dir": settings.video_dir,
            },
        },
    )
