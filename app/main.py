import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.video import router as video_router
from app.config import settings
from app.database import close_db, init_db
from app.middleware.auth import AdminAuthMiddleware
from app.utils.helpers import create_directory_structure

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(settings.log_file), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""

    # Startup
    logger.info("Starting Video Streaming Service...")

    # Create directory structure
    create_directory_structure()

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create admin user if it doesn't exist
    try:
        from create_admin import create_admin_user

        await create_admin_user()
    except Exception as e:
        logger.warning(f"Could not create admin user: {e}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Video Streaming Service...")
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Video Streaming Service with Admin Panel",
    debug=settings.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AdminAuthMiddleware, protected_paths=["/admin"])


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(video_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix="")


# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Root endpoint - redirect to admin panel"""
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "title": "Video Streaming Admin"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


# API Info endpoint
@app.get(f"{settings.api_prefix}/info")
async def api_info():
    """API information endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Video Streaming Service API",
        "endpoints": {
            "auth": f"{settings.api_prefix}/auth",
            "video": f"{settings.api_prefix}/video",
            "admin": "/admin",
            "docs": "/docs",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
