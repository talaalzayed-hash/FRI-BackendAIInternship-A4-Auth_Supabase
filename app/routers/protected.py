"""Stage 2 - the locked door, before the guard is hired.

The route only checks that a token was *presented*. It does not yet ask
Supabase whether the token is genuine, so a made-up string still gets in.
Stage 3 closes that hole.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header, status # type: ignore

from app.security import bearer_scheme, extract_bearer_token, json_error

router = APIRouter(prefix="/protected", tags=["protected"])

@router.get(
    "/profile",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(bearer_scheme)],  # shows the padlock; sends the header
)
def profile(
    # Read straight from the raw header and parse it ourselves. The scheme above
    # only handles the docs; include_in_schema=False hides the duplicate (and
    # spec-ignored) "authorization" box that Swagger would never transmit.
    authorization: Optional[str] = Header(default=None, include_in_schema=False),
):
    """Read private profile data - requires `Authorization: Bearer <token>`."""
    token = extract_bearer_token(authorization)
    if token is None:
        return json_error(status.HTTP_401_UNAUTHORIZED, "Access token required")
    # A token was presented. Not verified yet - see Stage 3.
    return {
        "message": "Access token received",
        "verified": False,
        "token_length": len(token),
    }
