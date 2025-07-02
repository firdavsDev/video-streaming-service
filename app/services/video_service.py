import logging
import os
from typing import Optional

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.tasks.video_tasks import process_video
from app.utils.helpers import get_file_size, paginate_query, validate_video_file
from app.utils.security import generate_secure_filename, generate_video_token

logger = logging.getLogger(__name__)


class VideoService:
    def __init__(self, db: Session):
        self.db = db

    async def upload_video(
        self, file: UploadFile, title: str, description: str, user: User
    ) -> Video:
        """Handle video upload"""

        # Validate file
        validate_video_file(file)

        try:
            # Create video record
            video = Video(
                title=title,
                description=description,
                original_filename=file.filename,
                status=VideoStatus.UPLOADING,
                uploaded_by_id=user.id,
                upload_progress=0,
            )

            self.db.add(video)
            self.db.commit()
            self.db.refresh(video)

            logger.info(f"Created video record with ID: {video.id}")

            # Generate secure filename for temporary storage
            temp_filename = generate_secure_filename(file.filename)
            temp_path = os.path.join(settings.upload_dir, "temp", temp_filename)

            # Ensure temp directory exists
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)

            # Save uploaded file to temporary location
            await self._save_upload_file(file, temp_path)

            # Update video record with progress
            video.upload_progress = 5
            self.db.commit()

            # Start background processing task
            task = process_video.delay(video.id, temp_path)

            logger.info(f"Started processing task {task.id} for video {video.id}")

            return video

        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            # Clean up video record if created
            if "video" in locals():
                self.db.delete(video)
                self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}",
            )

    async def _save_upload_file(self, upload_file: UploadFile, destination: str):
        """Save uploaded file to destination"""
        try:
            async with aiofiles.open(destination, "wb") as f:
                chunk_size = 1024 * 1024  # 1MB chunks
                while chunk := await upload_file.read(chunk_size):
                    await f.write(chunk)

            logger.info(f"File saved to: {destination}")

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            # Clean up partial file
            if os.path.exists(destination):
                os.remove(destination)
            raise

    def get_video_by_id(self, video_id: int, user: User) -> Optional[Video]:
        """Get video by ID (admin can see all, users see only their own)"""
        query = self.db.query(Video).filter(Video.id == video_id)

        if not user.is_admin:
            query = query.filter(Video.uploaded_by_id == user.id)

        return query.first()

    def get_video_by_unique_id(self, unique_id: str) -> Optional[Video]:
        """Get video by unique ID"""
        return self.db.query(Video).filter(Video.unique_id == unique_id).first()

    def get_user_videos(
        self,
        user: User,
        page: int = 1,
        per_page: int = 10,
        status_filter: Optional[VideoStatus] = None,
    ) -> dict:
        """Get paginated list of user's videos"""
        query = self.db.query(Video)

        if not user.is_admin:
            query = query.filter(Video.uploaded_by_id == user.id)

        if status_filter:
            query = query.filter(Video.status == status_filter)

        query = query.order_by(Video.created_at.desc())

        return paginate_query(query, page, per_page)

    def get_all_videos(
        self,
        page: int = 1,
        per_page: int = 10,
        status_filter: Optional[VideoStatus] = None,
    ) -> dict:
        """Get paginated list of all videos (admin only)"""
        query = self.db.query(Video)

        if status_filter:
            query = query.filter(Video.status == status_filter)

        query = query.order_by(Video.created_at.desc())

        return paginate_query(query, page, per_page)

    def update_video(
        self,
        video_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        user: User = None,
    ) -> Optional[Video]:
        """Update video information"""
        video = self.get_video_by_id(video_id, user)

        if not video:
            return None

        if title is not None:
            video.title = title

        if description is not None:
            video.description = description

        self.db.commit()
        self.db.refresh(video)

        logger.info(f"Updated video {video_id}")
        return video

    def delete_video(self, video_id: int, user: User) -> bool:
        """Delete video and associated files"""
        video = self.get_video_by_id(video_id, user)

        if not video:
            return False

        try:
            # Delete physical files
            if video.file_path and os.path.exists(video.file_path):
                os.remove(video.file_path)
                logger.info(f"Deleted video file: {video.file_path}")

            if video.thumbnail_path and os.path.exists(video.thumbnail_path):
                os.remove(video.thumbnail_path)
                logger.info(f"Deleted thumbnail: {video.thumbnail_path}")

            # Update status instead of deleting record (for audit trail)
            video.status = VideoStatus.DELETED
            self.db.commit()

            logger.info(f"Video {video_id} marked as deleted")
            return True

        except Exception as e:
            logger.error(f"Error deleting video {video_id}: {e}")
            self.db.rollback()
            return False

    def generate_streaming_token(self, video_id: int, user: User) -> Optional[str]:
        """Generate secure token for video streaming"""
        video = self.get_video_by_id(video_id, user)

        if not video or video.status != VideoStatus.COMPLETED:
            return None

        return generate_video_token(video.id, user.id)

    def get_video_stats(self, user: User) -> dict:
        """Get video statistics"""
        query = self.db.query(Video)

        if not user.is_admin:
            query = query.filter(Video.uploaded_by_id == user.id)

        total_videos = query.count()
        completed_videos = query.filter(Video.status == VideoStatus.COMPLETED).count()
        processing_videos = query.filter(
            Video.status.in_([VideoStatus.UPLOADING, VideoStatus.PROCESSING])
        ).count()
        failed_videos = query.filter(Video.status == VideoStatus.FAILED).count()

        # Calculate total file size
        total_size = (
            query.filter(Video.file_size.isnot(None))
            .with_entities(self.db.func.sum(Video.file_size))
            .scalar()
            or 0
        )

        return {
            "total_videos": total_videos,
            "completed_videos": completed_videos,
            "processing_videos": processing_videos,
            "failed_videos": failed_videos,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
