"""FastAPI auth middleware — API-key based with timing-safe comparison."""

import hmac
import secrets
from fastapi import HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from cybernetics.config.settings import settings
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.auth")
security = HTTPBearer(auto_error=False)


class APIKeyAuth(BaseHTTPMiddleware):
    """Middleware that validates a static API key on every request.
    Skips health and OpenAPI docs."""

    SKIP_PATHS = {"/health", "/openapi.json", "/docs", "/redoc"}

    def __init__(self, app):
        super().__init__(app)
        self._expected_key = settings.broker_api_key.encode("utf-8")

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("missing_or_invalid_auth", path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        provided = auth_header[7:].encode("utf-8")
        if not hmac.compare_digest(provided, self._expected_key):
            # Random delay to mitigate timing attacks
            secrets.token_hex(32)
            logger.warning("invalid_api_key", path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


def require_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency for individual endpoints."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expected = settings.broker_api_key.encode("utf-8")
    provided = credentials.credentials.encode("utf-8")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
