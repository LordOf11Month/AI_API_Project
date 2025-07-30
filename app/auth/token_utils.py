import jwt
from datetime import datetime, timedelta, timezone
import os
from fastapi import HTTPException
from app.utils import console_logger


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-default-secret-key")
ALGORITHM = "HS256"

def create_token(client_id: str, expires_delta: timedelta = timedelta(minutes=15)) -> str:
    """
    Creates a JWT token.
    """
    console_logger.info(f"Creating token for client_id: {client_id}", "[Token]")
    console_logger.debug(f"Token expires in: {expires_delta}", "[Token]")
    
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"client_id": client_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    console_logger.info("Token created successfully", "[Token]")
    console_logger.debug(f"Token expiration time: {expire}", "[Token]")
    
    return encoded_jwt

def verify_token(token: str) -> dict:
    """
    Verifies the JWT token.
    """
    console_logger.info("Verifying JWT token", "[Token]")
    console_logger.debug(f"Token to verify: {token[:20]}...", "[Token]")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        console_logger.info("Token verified successfully", "[Token]")
        console_logger.debug(f"Token payload: {payload}", "[Token]")
        return payload
    except jwt.ExpiredSignatureError:
        console_logger.error("Token verification failed: Token has expired", "[Token]")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        console_logger.error("Token verification failed: Invalid token", "[Token]")
        raise HTTPException(status_code=401, detail="Invalid token") 