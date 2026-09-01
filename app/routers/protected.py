"""Stage 3 - the guard at the door.

Stage 2 only checked that a pass was *presented*. Now we hand the token to
Supabase and let it tell us whether the pass is genuine. That is a network
call, not a local guess, so the answer is trustworthy: a token we never
issued, one whose payload was edited, or one that has expired all fail here.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header, status # type: ignore
from fastapi.encoders import jsonable_encoder # type: ignore

from app.database.database import supabase
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
    """Read private profile data - requires a valid `Authorization: Bearer <token>`."""
    token = extract_bearer_token(authorization)
    if token is None:
        # Nothing was presented. Different failure from "presented, but fake".
        return json_error(status.HTTP_401_UNAUTHORIZED, "Access token required")

    try:
        result = supabase.auth.get_user(token)
    except Exception:
        # Supabase rejected it: expired, tampered with, malformed, or revoked.
        # The reason is deliberately not echoed back - it would only help an
        # attacker tune their next guess.
        return json_error(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    # Belt and braces: some client versions answer with an empty user instead
    # of raising, and an empty user must never count as a pass.
    if result is None or result.user is None:
        return json_error(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = result.user
    # Safe metadata only. Never return the token, the session, or anything
    # from app_metadata / the service role - the caller already has their
    # token, and everything else is need-to-know.
    return {
        "id": str(user.id),
        "email": user.email,
        "created_at": jsonable_encoder(user.created_at),
    }
