"""
JWT Token Utilities

This module provides utility functions for creating and verifying JSON Web Tokens
(JWTs) used for client authentication. It relies on the PyJWT library and uses
a secret key from environment variables.

Key Functions:
- create_token: Creates a new JWT for a given client ID with a specified
  expiration time.
- verify_token: Verifies a JWT's signature and expiration, returning its payload.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""
import jwt
from datetime import datetime, timedelta, timezone
import os
from fastapi import HTTPException
from app.utils import console_logger


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-default-secret-key")
ALGORITHM = "HS256"

def create_token(client_id: str, expires_delta: timedelta = timedelta(minutes=15)) -> str:
    """
    Creates a new JWT for a given client ID.
    
    Args:
        client_id (str): The unique identifier of the client to include in the token.
        expires_delta (timedelta): The lifespan of the token. Defaults to 15 minutes.
        
    Returns:
        str: The encoded JWT string.
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
    Verifies a JWT's signature and expiration.
    
    Args:
        token (str): The JWT string to verify.
        
    Returns:
        dict: The decoded token payload if verification is successful.
        
    Raises:
        HTTPException: 
            - 401: If the token has expired or is invalid.
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