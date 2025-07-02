from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.video import VideoStatus


class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None


class VideoCreate(VideoBase):
    pass


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class VideoResponse(VideoBase):
    id: int
    unique_id: str
    original_filename: str
    file_size: Optional[int] = None
    duration: Optional[int] = None
    resolution: Optional[str] = None
    format: Optional[str] = None
    status: VideoStatus
    upload_progress: int
    streaming_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    uploaded_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0

    @property
    def duration_formatted(self) -> str:
        if not self.duration:
            return "00:00:00"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class VideoListResponse(BaseModel):
    items: List[VideoResponse]
    total: int
    page: int
    per_page: int
    pages: int


class VideoUploadResponse(BaseModel):
    id: int
    unique_id: str
    title: str
    status: VideoStatus
    upload_progress: int
    message: str


class VideoStatsResponse(BaseModel):
    total_videos: int
    completed_videos: int
    processing_videos: int
    failed_videos: int
    total_size_bytes: int
    total_size_mb: float


class VideoStreamResponse(BaseModel):
    streaming_url: str
    token: str
    expires_in: int


class VideoProgressResponse(BaseModel):
    video_id: int
    status: VideoStatus
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
