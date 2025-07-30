from fastapi import Request, HTTPException, Depends
from app.auth.token_utils import verify_token
from app.utils import console_logger

def get_current_client_id(request: Request) -> str:
    """
    FastAPI dependency to get the current client_id from the Authorization header.
    """
    console_logger.info("Processing authentication request", "[Auth]")
    
    auth_header = request.headers.get("Authorization")
    console_logger.debug(f"Authorization header present: {auth_header is not None}", "[Auth]")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        console_logger.warning("Missing or invalid authorization header", "[Auth]")
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    console_logger.debug("Token extracted from header", "[Auth]")
    
    try:
        payload = verify_token(token)
        client_id = payload.get("client_id")
        console_logger.debug(f"Client ID extracted from token: {client_id}", "[Auth]")
        
        if client_id is None:
            console_logger.error("Invalid token payload: missing client_id", "[Auth]")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        console_logger.info(f"Authentication successful for client: {client_id}", "[Auth]")
        return client_id
    except HTTPException as e:
        console_logger.error(f"Token verification failed: {e.detail}", "[Auth]")
        # Re-raising the exception from verify_token
        raise e
    except Exception:
        console_logger.error("Unexpected error during authentication", "[Auth]")
        raise HTTPException(status_code=401, detail="Could not validate credentials") 