"""Protected routes. Notice how little auth code lives here now.

The handler below says `Depends(get_current_user)` and then gets on with
its job. The guard has already verified the token and injected the user; if
it had not, the function body would never have been entered. Any new route
is protected by adding that one parameter - no auth code gets rewritten.
"""
from fastapi import APIRouter, Depends, status # type: ignore

from app.security import CurrentUser, get_current_user

router = APIRouter(prefix="/protected", tags=["protected"])

@router.get("/profile", status_code=status.HTTP_200_OK)
def profile(current_user: CurrentUser = Depends(get_current_user)):
    """Read private profile data. Requires a valid access token."""
    return current_user.public_profile()
