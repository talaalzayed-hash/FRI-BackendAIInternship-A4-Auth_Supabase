from fastapi import FastAPI # type: ignore
from app.database.database import supabase # type: ignore

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Auth API is running"}
