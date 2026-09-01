"""Shared auth helpers.

Stage 2 only inspects the Authorization header; Stage 3 will hand the token
it extracts to Supabase for real verification, and Stage 4 will wrap that
into one reusable dependency. Keeping the parsing here means all three
stages read the header exactly the same way.
"""
from typing import Optional
from fastapi.responses import JSONResponse # type: ignore
from fastapi.security import HTTPBearer # type: ignore

# Declaring the scheme is what puts the "Authorize" padlock in Swagger UI and
# makes it send a real Authorization header. OpenAPI forbids documenting
# "Authorization" as an ordinary header parameter, so Swagger silently drops
# such a box - the token never leaves the browser and every call looks like a
# missing token. auto_error=False keeps this purely declarative: it never
# raises its own 403, so our own 401 + message stays the single source of truth.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the access_token returned by POST /auth/login.",
)

def json_error(status_code: int, message: str) -> JSONResponse:
    """Every failure in this API leaves the same shape: {"error": "..."}."""
    return JSONResponse(
        status_code=status_code,
        content={"error": message},
        headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
    )

def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Pull the token out of `Authorization: Bearer <token>`.

    Returns None when the header is missing, is not the Bearer scheme, or
    carries no token, so the caller can answer 401. Nothing here checks
    whether the token is *real* - that is Stage 3's job.
    """
    if not authorization:
        return None
    parts = authorization.split()
    # A well-formed header is exactly two words: the scheme and the token.
    if len(parts) != 2:
        return None
    scheme, token = parts
    # RFC 7235: the scheme name is case-insensitive.
    if scheme.lower() != "bearer":
        return None
    if not token.strip():
        return None
    return token
