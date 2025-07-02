# app/config.py
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Get the correct path for .env file
# In Docker: /app/.env
# In development: ../
if os.path.exists("/app/.env"):
    ENV_FILE = "/app/.env"  # Docker container path
else:
    # Development path (app/ directory ke parent)
    ROOT_DIR = Path(__file__).parent.parent
    ENV_FILE = str(ROOT_DIR / ".env")


class Settings(BaseSettings):
    # Database
    database_url: str
    test_database_url: str | None = None

    # PostgreSQL (for Docker)
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # Redis
    redis_url: str

    # Security
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # Admin
    admin_username: str
    admin_password: str
    admin_email: str

    # File Storage
    upload_dir: str
    video_dir: str
    max_file_size: int
    allowed_video_types: str

    # Application
    app_name: str
    app_version: str
    debug: bool
    api_prefix: str

    # CORS
    allowed_origins: str

    # Celery
    celery_broker_url: str
    celery_result_backend: str

    # Logging
    log_level: str
    log_file: str

    class Config:
        env_file = ENV_FILE
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    @property
    def allowed_video_types_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        return [ext.strip() for ext in self.allowed_video_types.split(",")]

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


# Global settings instance
settings = Settings()
