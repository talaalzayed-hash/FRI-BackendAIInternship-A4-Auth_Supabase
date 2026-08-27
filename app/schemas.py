from typing import Optional

from pydantic import BaseModel

class AuthCredentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {"email": "test@example.com", "password": "password123"}
        }
    }
