from fastapi import APIRouter, status # type: ignore
from fastapi.encoders import jsonable_encoder # type: ignore
from fastapi.responses import JSONResponse

from app.database.database import supabase
from app.schemas import AuthCredentials
from app.security import json_error

router = APIRouter(prefix="/auth", tags=["auth"])

def _is_blank(value) -> bool:
    """True when a field is missing, empty, or only whitespace."""
    return value is None or not str(value).strip()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(credentials: AuthCredentials):
    """Create a new user account in Supabase."""
    # The server never trusts the client: check the body before calling out.
    if _is_blank(credentials.email) or _is_blank(credentials.password):
        return json_error(status.HTTP_400_BAD_REQUEST, "Email and password are required")
    try:
        result = supabase.auth.sign_up(
            {"email": credentials.email, "password": credentials.password}
        )
    except Exception as exc:  # e.g. weak password, invalid email, email taken
        return json_error(status.HTTP_400_BAD_REQUEST, str(exc))
    if result.user is None:
        return json_error(status.HTTP_400_BAD_REQUEST, "Sign up failed")
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "User created", "user": jsonable_encoder(result.user)},
    )

@router.post("/login", status_code=status.HTTP_200_OK)
def login(credentials: AuthCredentials):
    """Exchange email + password for a Supabase-signed JWT."""
    if _is_blank(credentials.email) or _is_blank(credentials.password):
        return json_error(status.HTTP_400_BAD_REQUEST, "Email and password are required")
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": credentials.email, "password": credentials.password}
        )
    except Exception:
        # Deliberately vague: never tell a caller which half was wrong.
        return json_error(status.HTTP_401_UNAUTHORIZED, "Invalid login credentials")
    if result.session is None:
        return json_error(status.HTTP_401_UNAUTHORIZED, "Invalid login credentials")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": result.session.token_type,
        "expires_in": result.session.expires_in,
        "user": jsonable_encoder(result.user),
    }
