import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta

from celery import current_task
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.utils.helpers import calculate_file_hash, get_file_size
from app.utils.security import generate_secure_filename
from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_video(self, video_id: int, temp_file_path: str):
    """Process uploaded video file"""

    db: Session = SessionLocal()

    try:
        # Get video record
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video with ID {video_id} not found")
            return {"error": "Video not found"}

        # Update status to processing
        video.status = VideoStatus.PROCESSING
        video.upload_progress = 10
        video.processing_log = "Starting video processing..."
        db.commit()

        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "status": "Starting processing..."},
        )

        # Validate file exists
        if not os.path.exists(temp_file_path):
            raise Exception(f"Temporary file not found: {temp_file_path}")

        # Get file info
        file_size = get_file_size(temp_file_path)
        file_hash = calculate_file_hash(temp_file_path)

        video.file_size = file_size
        video.upload_progress = 20
        video.processing_log += "\nFile validation completed..."
        db.commit()

        self.update_state(
            state="PROGRESS",
            meta={"current": 20, "total": 100, "status": "Validating file..."},
        )

        # Extract video metadata using ffprobe
        metadata = extract_video_metadata(temp_file_path)

        video.duration = metadata.get("duration")
        video.resolution = metadata.get("resolution")
        video.format = metadata.get("format")
        video.upload_progress = 40
        video.processing_log += f"\nMetadata extracted: {metadata}"
        db.commit()

        self.update_state(
            state="PROGRESS",
            meta={"current": 40, "total": 100, "status": "Extracting metadata..."},
        )

        # Generate secure filename and move to final location
        secure_filename = generate_secure_filename(video.original_filename)
        final_path = os.path.join(settings.video_dir, "processed", secure_filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        # Process video (convert if needed)
        processed_path = process_video_file(temp_file_path, final_path, self)

        video.file_path = processed_path
        video.upload_progress = 80
        video.processing_log += f"\nVideo processed successfully: {processed_path}"
        db.commit()

        self.update_state(
            state="PROGRESS",
            meta={"current": 80, "total": 100, "status": "Generating thumbnail..."},
        )

        # Generate thumbnail
        thumbnail_path = generate_thumbnail(processed_path, video.id)
        video.thumbnail_path = thumbnail_path

        # Generate streaming URL
        streaming_url = f"/api/v1/video/stream/{video.unique_id}"
        video.streaming_url = streaming_url

        # Update final status
        video.status = VideoStatus.COMPLETED
        video.upload_progress = 100
        video.completed_at = datetime.utcnow()
        video.processing_log += "\nVideo processing completed successfully!"
        db.commit()

        # Clean up temporary file
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logger.warning(f"Failed to remove temp file: {e}")

        logger.info(f"Video {video_id} processed successfully")

        return {
            "video_id": video_id,
            "status": "completed",
            "file_path": processed_path,
            "streaming_url": streaming_url,
            "duration": video.duration,
            "file_size": video.file_size,
        }

    except Exception as e:
        logger.error(f"Error processing video {video_id}: {e}")

        # Update video status to failed
        if "video" in locals():
            video.status = VideoStatus.FAILED
            video.error_message = str(e)
            video.processing_log += f"\nError: {str(e)}"
            db.commit()

        # Clean up temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up temp file: {cleanup_error}")

        return {"error": str(e), "video_id": video_id}

    finally:
        db.close()


def extract_video_metadata(file_path: str) -> dict:
    """Extract video metadata using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            logger.warning(f"ffprobe failed: {result.stderr}")
            return {}

        data = json.loads(result.stdout)

        # Extract video stream info
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        metadata = {}

        if video_stream:
            metadata["resolution"] = (
                f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}"
            )
            metadata["format"] = video_stream.get("codec_name", "unknown")

        format_info = data.get("format", {})
        duration = float(format_info.get("duration", 0))
        metadata["duration"] = int(duration) if duration > 0 else None

        return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}


def process_video_file(input_path: str, output_path: str, task=None) -> str:
    """Process video file (convert to standard format if needed)"""
    try:
        # Check if we want to enable video conversion
        enable_conversion = (
            os.getenv("ENABLE_VIDEO_CONVERSION", "false").lower() == "true"
        )

        if task:
            task.update_state(
                state="PROGRESS",
                meta={"current": 60, "total": 100, "status": "Processing video..."},
            )

        if enable_conversion:
            # Convert video using FFmpeg
            cmd = [
                "ffmpeg",
                "-i",
                input_path,
                "-c:v",
                "libx264",  # H.264 video codec
                "-preset",
                "medium",  # Encoding speed vs quality
                "-crf",
                "23",  # Quality (18-28, lower=better)
                "-c:a",
                "aac",  # Audio codec
                "-b:a",
                "128k",  # Audio bitrate
                "-movflags",
                "+faststart",  # Enable web streaming
                "-y",  # Overwrite output file
                output_path,
            ]

            logger.info(f"Converting video with FFmpeg: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=1800
            )  # 30 minutes timeout

            if result.returncode != 0:
                logger.error(f"FFmpeg conversion failed: {result.stderr}")
                raise Exception(f"Video conversion failed: {result.stderr}")

            logger.info("Video conversion completed successfully")
        else:
            # Simple copy without conversion (faster for development)
            logger.info("Copying video file without conversion")
            shutil.copy2(input_path, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        logger.error("Video conversion timed out")
        raise Exception("Video conversion timed out after 30 minutes")
    except Exception as e:
        logger.error(f"Error processing video file: {e}")
        raise


def generate_thumbnail(video_path: str, video_id: int) -> str:
    """Generate video thumbnail"""
    try:
        thumbnail_dir = os.path.join(settings.video_dir, "thumbnails")
        os.makedirs(thumbnail_dir, exist_ok=True)

        thumbnail_path = os.path.join(thumbnail_dir, f"thumb_{video_id}.jpg")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-ss",
            "00:00:01",  # Take screenshot at 1 second
            "-vframes",
            "1",
            "-vf",
            "scale=320:240",
            "-y",  # Overwrite output file
            thumbnail_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if result.returncode == 0:
            return thumbnail_path
        else:
            logger.warning(f"Thumbnail generation failed: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None


@celery_app.task
def cleanup_temp_files():
    """Clean up old temporary files"""
    try:
        temp_dir = os.path.join(settings.upload_dir, "temp")
        if not os.path.exists(temp_dir):
            return

        cutoff_time = datetime.now() - timedelta(hours=24)  # Files older than 24 hours
        cleaned_count = 0

        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)

            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"Removed old temp file: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {filename}: {e}")

        logger.info(f"Cleanup completed. Removed {cleaned_count} old temp files.")
        return {"cleaned_files": cleaned_count}

    except Exception as e:
        logger.error(f"Error during temp file cleanup: {e}")
        return {"error": str(e)}
