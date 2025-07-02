import hashlib
import logging
import mimetypes
import os

from fastapi import HTTPException, UploadFile, status

from app.config import settings

logger = logging.getLogger(__name__)


def validate_video_file(file: UploadFile) -> bool:
    """Validate uploaded video file"""

    # Check file size
    if hasattr(file, "size") and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_file_size / (1024*1024):.0f}MB",
        )

    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required"
        )

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in settings.allowed_video_types_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(settings.allowed_video_types_list)}",
        )

    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file.filename)
    if mime_type and not mime_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a video"
        )

    return True


def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""


def ensure_directory_exists(directory: str) -> bool:
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting file size: {e}")
        return 0


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def clean_filename(filename: str) -> str:
    """Clean filename for safe storage"""
    # Remove or replace unsafe characters
    unsafe_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    clean_name = filename

    for char in unsafe_chars:
        clean_name = clean_name.replace(char, "_")

    # Limit length
    name, ext = os.path.splitext(clean_name)
    if len(name) > 100:
        name = name[:100]

    return f"{name}{ext}"


def paginate_query(query, page: int = 1, per_page: int = 10):
    """Add pagination to SQLAlchemy query"""
    if page < 1:
        page = 1

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


def create_directory_structure():
    """Create necessary directory structure"""
    directories = [
        settings.upload_dir,
        settings.video_dir,
        f"{settings.upload_dir}/temp",
        f"{settings.video_dir}/processed",
        "logs",
    ]

    for directory in directories:
        ensure_directory_exists(directory)

    logger.info("Directory structure created successfully")

    logger.info("Directory structure created successfully")
