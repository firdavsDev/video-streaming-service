import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.database import SessionLocal
from app.utils.security import verify_token

logger = logging.getLogger(__name__)


import logging

logger = logging.getLogger(__name__)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to protect admin routes"""

    def __init__(self, app, protected_paths: list = None):
        super().__init__(app)
        self.protected_paths = protected_paths or ["/admin"]

    async def dispatch(self, request: Request, call_next):
        # Check if the path requires admin authentication
        path = request.url.path

        # Skip authentication for certain paths
        skip_paths = [
            "/auth/login",
            "/auth/login-json",
            "/admin/login",  # Admin login page
            "/admin/logout",  # Admin logout
            "/admin/debug",  # Debug endpoint
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/health",  # Health check
            "/",  # Root path
        ]

        if any(path.startswith(skip_path) for skip_path in skip_paths):
            logger.info(f"Skipping authentication for path: {path}")
            return await call_next(request)

        # Check if path requires admin access
        if any(
            path.startswith(protected_path) for protected_path in self.protected_paths
        ):
            logger.info(f"Admin middleware - Protecting path: {path}")

            # Get token from header or cookie
            token = None

            # Try to get token from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

            # Try to get token from cookie
            if not token:
                token = request.cookies.get("access_token")

            # Debug logging
            logger.info(f"Admin middleware - Path: {path}")
            logger.info(f"Admin middleware - Cookies: {dict(request.cookies)}")
            logger.info(f"Admin middleware - Token found: {bool(token)}")

            if not token:
                logger.info("Admin middleware - No token found, redirecting to login")
                return RedirectResponse(
                    url="/admin/login", status_code=status.HTTP_302_FOUND
                )

            try:
                # Verify token
                payload = verify_token(token)
                logger.info(f"Admin middleware - Token payload: {payload}")

                # Check if user is admin
                if not payload.get("is_admin", False):
                    logger.info(
                        "Admin middleware - User is not admin, redirecting to login"
                    )
                    return RedirectResponse(
                        url="/admin/login", status_code=status.HTTP_302_FOUND
                    )

                # Add user info to request state
                request.state.user_id = payload.get("user_id")
                request.state.username = payload.get("sub")
                request.state.is_admin = payload.get("is_admin", False)
                logger.info(
                    f"Admin middleware - User authenticated: {request.state.username}"
                )

            except HTTPException as e:
                logger.error(f"Admin middleware - Token verification failed: {e}")
                return RedirectResponse(
                    url="/admin/login", status_code=status.HTTP_302_FOUND
                )

        response = await call_next(request)
        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware"""

    def __init__(self, app, allowed_origins: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)

        # Add CORS headers
        origin = request.headers.get("origin")
        if origin in self.allowed_origins or "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"

        return response
