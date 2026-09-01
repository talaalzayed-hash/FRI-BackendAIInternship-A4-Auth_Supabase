"""Stage 2 - the public lobby. No auth, no token, anyone may enter."""
from fastapi import APIRouter, status # type: ignore

router = APIRouter(prefix="/public", tags=["public"])

@router.get("/info", status_code=status.HTTP_200_OK)
def info():
    """Open data - deliberately requires no Authorization header."""
    return {"message": "Welcome stranger! This info is public."}
