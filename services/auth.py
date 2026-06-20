import time
from fastapi import Request, HTTPException, Query
from starlette.responses import JSONResponse
from services.db import get_connection, close_connection
from services.rate_limiter import RateLimiter

rate_limiter = RateLimiter(default_limit=120, window_seconds=60)

def get_api_key(request: Request, api_key: str = Query(None)):
    """Dual-source API key: X-API-Key header takes priority, query param as fallback."""
    header_key = request.headers.get("X-API-Key")
    key = header_key or api_key
    if not key:
        raise HTTPException(status_code=401, detail="Missing API key (use X-API-Key header or api_key param)")
    from app.dependencies.auth import VALID_KEYS
    if key not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if api_key and not header_key:
        import warnings
        warnings.warn("API key via query param is deprecated. Use X-API-Key header.", DeprecationWarning, stacklevel=2)
    return VALID_KEYS[key]
