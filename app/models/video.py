import enum
import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class VideoStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(
        String(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # File information
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to processed video
    file_size = Column(BigInteger, nullable=True)  # Size in bytes
    duration = Column(Integer, nullable=True)  # Duration in seconds
    resolution = Column(String(20), nullable=True)  # e.g., "1920x1080"
    format = Column(String(10), nullable=True)  # e.g., "mp4"

    # Processing status
    status = Column(Enum(VideoStatus), default=VideoStatus.UPLOADING, index=True)
    upload_progress = Column(Integer, default=0)  # Progress percentage
    processing_log = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Streaming information
    streaming_url = Column(String(500), nullable=True)  # Secure streaming URL
    thumbnail_path = Column(String(500), nullable=True)

    # Relationships
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_by = relationship("User", back_populates="videos")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', status='{self.status}')>"

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0

    @property
    def duration_formatted(self):
        """Return formatted duration (HH:MM:SS)"""
        if not self.duration:
            return "00:00:00"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def is_completed(self):
        return self.status == VideoStatus.COMPLETED

    @property
    def is_processing(self):
        return self.status in [VideoStatus.UPLOADING, VideoStatus.PROCESSING]

    @property
    def has_error(self):
        return self.status == VideoStatus.FAILED @ property

    def is_completed(self):
        return self.status == VideoStatus.COMPLETED

    @property
    def is_processing(self):
        return self.status in [VideoStatus.UPLOADING, VideoStatus.PROCESSING]

    @property
    def has_error(self):
        return self.status == VideoStatus.FAILED
