import jwt
from datetime import datetime, timedelta
import os
from fastapi import HTTPException

# It's crucial to load the secret key from the environment variables
# for security reasons. Do not hardcode it.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-default-secret-key")
ALGORITHM = "HS256"

def create_token(client_id: str, expires_delta: timedelta = timedelta(minutes=15)) -> str:
    """
    Creates a JWT token.
    """
    expire = datetime.utcnow() + expires_delta
    to_encode = {"client_id": client_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """
    Verifies the JWT token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token") 