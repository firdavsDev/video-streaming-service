import logging
import os
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.video import VideoStatus
from app.schemas.video import (
    VideoListResponse,
    VideoResponse,
    VideoStatsResponse,
    VideoUpdate,
    VideoUploadResponse,
)
from app.services.auth_service import get_current_admin_user, get_current_user_optional
from app.services.video_service import VideoService
from app.utils.security import verify_video_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["Video"])


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Upload a new video (Admin only)"""

    video_service = VideoService(db)

    try:
        video = await video_service.upload_video(
            file=file, title=title, description=description, user=current_admin
        )

        return VideoUploadResponse(
            id=video.id,
            unique_id=video.unique_id,
            title=video.title,
            status=video.status,
            upload_progress=video.upload_progress,
            message="Video upload started successfully",
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/list", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status_filter: Optional[VideoStatus] = Query(None),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get list of videos (Admin only)"""

    video_service = VideoService(db)
    result = video_service.get_user_videos(
        user=current_admin, page=page, per_page=per_page, status_filter=status_filter
    )

    return VideoListResponse(**result)


@router.get("/stats", response_model=VideoStatsResponse)
async def get_video_stats(
    current_admin: User = Depends(get_current_admin_user), db: Session = Depends(get_db)
):
    """Get video statistics (Admin only)"""

    video_service = VideoService(db)
    stats = video_service.get_video_stats(current_admin)

    return VideoStatsResponse(**stats)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get video details (Admin only)"""

    video_service = VideoService(db)
    video = video_service.get_video_by_id(video_id, current_admin)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    return VideoResponse.from_orm(video)


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Update video information (Admin only)"""

    video_service = VideoService(db)
    video = video_service.update_video(
        video_id=video_id,
        title=video_update.title,
        description=video_update.description,
        user=current_admin,
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    return VideoResponse.from_orm(video)


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete video (Admin only)"""

    video_service = VideoService(db)
    success = video_service.delete_video(video_id, current_admin)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or could not be deleted",
        )

    return {"message": "Video deleted successfully"}


@router.get("/stream/{unique_id}")
async def stream_video(
    unique_id: str,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Stream video with token verification"""

    video_service = VideoService(db)
    video = video_service.get_video_by_unique_id(unique_id)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    if video.status != VideoStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not ready for streaming",
        )

    # Verify video token if provided
    if token:
        try:
            token_data = verify_video_token(token)
            if token_data.get("video_id") != video.id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid video token",
                )
        except HTTPException:
            raise
    elif not current_user or not current_user.is_admin:
        # Require token for non-admin users
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Video token required"
        )

    # Check if file exists
    if not video.file_path or not os.path.exists(video.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found"
        )

    # Stream the video file
    def iterfile(file_path: str):
        with open(file_path, mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(
        iterfile(video.file_path),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f"inline; filename={video.original_filename}",
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/thumbnail/{video_id}")
async def get_video_thumbnail(
    video_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get video thumbnail"""

    video_service = VideoService(db)

    # Allow thumbnail access for admin or with valid context
    if current_user and current_user.is_admin:
        video = video_service.get_video_by_id(video_id, current_user)
    else:
        # For public access, you might want to add additional checks
        video = (
            video_service.get_video_by_id(video_id, current_user)
            if current_user
            else None
        )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    if not video.thumbnail_path or not os.path.exists(video.thumbnail_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found"
        )

    return FileResponse(
        video.thumbnail_path,
        media_type="image/jpeg",
        filename=f"thumbnail_{video.id}.jpg",
    )


@router.get("/progress/{video_id}")
async def get_video_progress(
    video_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get video processing progress (Admin only)"""

    video_service = VideoService(db)
    video = video_service.get_video_by_id(video_id, current_admin)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    return {
        "video_id": video.id,
        "status": video.status,
        "progress": video.upload_progress,
        "message": video.processing_log,
        "error": video.error_message,
    }


@router.post("/{video_id}/generate-token")
async def generate_streaming_token(
    video_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Generate secure streaming token for video (Admin only)"""

    video_service = VideoService(db)
    token = video_service.generate_streaming_token(video_id, current_admin)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not ready for streaming",
        )

    video = video_service.get_video_by_id(video_id, current_admin)

    return {
        "streaming_url": f"{settings.api_prefix}/video/stream/{video.unique_id}?token={token}",
        "token": token,
        "expires_in": 3600,  # 1 hour
        "video_id": video_id,
    }
