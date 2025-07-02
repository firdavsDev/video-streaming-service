import asyncio
import os
import sys

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.models.user import User
from app.utils.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_admin_user():
    """Create admin user if it doesn't exist"""

    # Initialize database
    await init_db()

    db: Session = SessionLocal()
    try:
        # Check if admin user exists
        admin_user = (
            db.query(User).filter(User.username == settings.admin_username).first()
        )

        if admin_user:
            logger.info(f"Admin user '{settings.admin_username}' already exists")
            return admin_user

        # Create admin user
        hashed_password = get_password_hash(settings.admin_password)
        admin_user = User(
            username=settings.admin_username,
            email=settings.admin_email,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True,
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        logger.info(f"Admin user '{settings.admin_username}' created successfully")
        logger.info(f"Admin email: {settings.admin_email}")
        logger.info(f"Admin password: {settings.admin_password}")

        return admin_user

    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
    logger.info("Admin user creation script completed")
