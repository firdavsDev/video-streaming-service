# from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Text
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from app.database import Base


# class WatchProgress(Base):
#     __tablename__ = "watch_progress"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)

#     # Progress tracking
#     last_position = Column(Float, default=0.0)  # Last watched position in seconds
#     total_watched_time = Column(Float, default=0.0)  # Total time watched in seconds
#     watch_percentage = Column(Float, default=0.0)  # Percentage of video watched

#     # Completion status
#     is_completed = Column(Boolean, default=False)
#     completed_at = Column(DateTime(timezone=True), nullable=True)

#     # Watch sessions
#     session_count = Column(Integer, default=1)
#     first_watch_at = Column(DateTime(timezone=True), server_default=func.now())
#     last_watch_at = Column(
#         DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
#     )

#     # Security tracking
#     watched_segments = Column(Text, nullable=True)  # JSON string of watched segments
#     skip_attempts = Column(Integer, default=0)  # Number of skip attempts

#     # Relationships
#     user = relationship("User")
#     video = relationship("Video")

#     def __repr__(self):
#         return f"<WatchProgress(user_id={self.user_id}, video_id={self.video_id}, progress={self.watch_percentage}%)>"


# import json
# from datetime import datetime
# from typing import Optional

# # app/api/watch_progress.py
# from fastapi import APIRouter, Depends, HTTPException, status
# from pydantic import BaseModel
# from sqlalchemy.orm import Session

# from app.database import get_db
# from app.models.user import User
# from app.models.video import Video
# from app.models.watch_progress import WatchProgress
# from app.services.auth_service import get_current_user_optional

# router = APIRouter(prefix="/watch-progress", tags=["Watch Progress"])


# class WatchProgressUpdate(BaseModel):
#     video_id: int
#     current_time: float
#     duration: float
#     watched_percentage: float
#     watched_segments: list[int]  # List of 5-second segments watched
#     is_completed: Optional[bool] = False


# class WatchProgressResponse(BaseModel):
#     video_id: int
#     last_position: float
#     total_watched_time: float
#     watch_percentage: float
#     is_completed: bool
#     session_count: int
#     skip_attempts: int


# @router.post("/update")
# async def update_watch_progress(
#     progress_data: WatchProgressUpdate,
#     current_user: Optional[User] = Depends(get_current_user_optional),
#     db: Session = Depends(get_db),
# ):
#     """Update user's watch progress for a video"""

#     if not current_user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
#         )

#     # Get or create watch progress record
#     progress = (
#         db.query(WatchProgress)
#         .filter(
#             WatchProgress.user_id == current_user.id,
#             WatchProgress.video_id == progress_data.video_id,
#         )
#         .first()
#     )

#     if not progress:
#         progress = WatchProgress(
#             user_id=current_user.id,
#             video_id=progress_data.video_id,
#             first_watch_at=datetime.utcnow(),
#         )
#         db.add(progress)
#     else:
#         progress.session_count += 1

#     # Update progress data
#     progress.last_position = progress_data.current_time
#     progress.watch_percentage = min(progress_data.watched_percentage, 100.0)
#     progress.total_watched_time = (
#         len(progress_data.watched_segments) * 5
#     )  # 5 seconds per segment
#     progress.watched_segments = json.dumps(progress_data.watched_segments)
#     progress.last_watch_at = datetime.utcnow()

#     # Check completion (90% watched)
#     if progress_data.watched_percentage >= 90 and not progress.is_completed:
#         progress.is_completed = True
#         progress.completed_at = datetime.utcnow()

#     db.commit()
#     db.refresh(progress)

#     return {
#         "message": "Progress updated successfully",
#         "progress": WatchProgressResponse(
#             video_id=progress.video_id,
#             last_position=progress.last_position,
#             total_watched_time=progress.total_watched_time,
#             watch_percentage=progress.watch_percentage,
#             is_completed=progress.is_completed,
#             session_count=progress.session_count,
#             skip_attempts=progress.skip_attempts,
#         ),
#     }


# @router.get("/{video_id}")
# async def get_watch_progress(
#     video_id: int,
#     current_user: Optional[User] = Depends(get_current_user_optional),
#     db: Session = Depends(get_db),
# ):
#     """Get user's watch progress for a video"""

#     if not current_user:
#         return {"progress": None}

#     progress = (
#         db.query(WatchProgress)
#         .filter(
#             WatchProgress.user_id == current_user.id, WatchProgress.video_id == video_id
#         )
#         .first()
#     )

#     if not progress:
#         return {"progress": None}

#     return {
#         "progress": WatchProgressResponse(
#             video_id=progress.video_id,
#             last_position=progress.last_position,
#             total_watched_time=progress.total_watched_time,
#             watch_percentage=progress.watch_percentage,
#             is_completed=progress.is_completed,
#             session_count=progress.session_count,
#             skip_attempts=progress.skip_attempts,
#         )
#     }


# @router.post("/{video_id}/skip-attempt")
# async def record_skip_attempt(
#     video_id: int,
#     current_user: Optional[User] = Depends(get_current_user_optional),
#     db: Session = Depends(get_db),
# ):
#     """Record a skip attempt (for monitoring)"""

#     if not current_user:
#         return {"message": "Not tracked"}

#     progress = (
#         db.query(WatchProgress)
#         .filter(
#             WatchProgress.user_id == current_user.id, WatchProgress.video_id == video_id
#         )
#         .first()
#     )

#     if progress:
#         progress.skip_attempts += 1
#         db.commit()

#     return {"message": "Skip attempt recorded"}
