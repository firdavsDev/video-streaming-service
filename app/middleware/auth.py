import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.database import SessionLocal
from app.services.auth_service import AuthService
from app.utils.security import verify_token

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
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
        ]

        if any(path.startswith(skip_path) for skip_path in skip_paths):
            return await call_next(request)

        # Check if path requires admin access
        if any(
            path.startswith(protected_path) for protected_path in self.protected_paths
        ):

            # Get token from header or cookie
            token = None

            # Try to get token from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

            # Try to get token from cookie
            if not token:
                token = request.cookies.get("access_token")

            if not token:
                if path.startswith("/admin") and not path.startswith("/admin/login"):
                    return RedirectResponse(url="/admin/login", status_code=302)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

            try:
                # Verify token
                payload = verify_token(token)

                # Check if user is admin
                if not payload.get("is_admin", False):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Admin access required",
                    )

                # Add user info to request state
                request.state.user_id = payload.get("user_id")
                request.state.username = payload.get("sub")
                request.state.is_admin = payload.get("is_admin", False)

            except HTTPException as e:
                if path.startswith("/admin") and not path.startswith("/admin/login"):
                    return RedirectResponse(url="/admin/login", status_code=302)
                else:
                    raise e

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
