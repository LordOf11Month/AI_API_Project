from fastapi import Request, HTTPException, Depends
from app.auth.token_utils import verify_token

def get_current_client_id(request: Request) -> str:
    """
    FastAPI dependency to get the current client_id from the Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        client_id = payload.get("client_id")
        if client_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return client_id
    except HTTPException as e:
        # Re-raising the exception from verify_token
        raise e
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials") 