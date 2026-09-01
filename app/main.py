from fastapi import FastAPI

from app.routers import auth, protected, public

app = FastAPI(
    title="Auth API",
    description="Supabase-backed authentication: sign up, log in, and protected routes.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(protected.router)
app.include_router(public.router)

@app.get("/", tags=["meta"])
def root():
    return {"message": "Auth API is running"}
