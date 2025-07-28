from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
from typing import AsyncIterable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from app.routers.Dispatcher import HANDLERS, dispatch_request
from app.models.DataModels import APIRequest, ClientCredentials
from app.DB_connection.chat_manager import create_chat
from app.DB_connection.client_manager import create_client, authenticate_client
from app.auth.token_utils import create_token
from app.auth.middleware import get_current_client_id

# Load environment variables from a .env file if it exists
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Configure clients on startup.
    """
    # Initialize database first as other services might depend on it
    try:
        from app.DB_connection.database import db_manager
        print("Initializing database connection...")
        # Access engine to trigger initialization
        if db_manager.engine is None:
            raise ValueError("Failed to initialize database connection")
        print("Database connection established successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Warning: GOOGLE_API_KEY environment variable not set.")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Warning: OPENAI_API_KEY environment variable not set.")

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("Warning: ANTHROPIC_API_KEY environment variable not set.")
        
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        print("Warning: DEEPSEEK_API_KEY environment variable not set.")
        
    yield
    
    # Cleanup on shutdown
    print("Closing database connections...")
    if db_manager.engine:
        db_manager.engine.dispose()
    print("Database connections closed")


app = FastAPI(
    title="Unified AI API",
    description="An API to interact with multiple AI providers.",
    version="1.0.0",
    lifespan=lifespan
)


async def _dispatch_and_respond(request: APIRequest, client_id: str):
    """
    Helper function to dispatch a request and format the HTTP response.
    """
    response = await dispatch_request(request, client_id)
    
    if request.stream:
        if isinstance(response, AsyncIterable):
            return StreamingResponse(response, media_type="text/event-stream")
        else:
            raise HTTPException(status_code=500, detail="Streaming was requested but is not supported or failed for this provider.")
    else:
        return {"response": response}


@app.post("/api/generate")
async def generate(request: APIRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handles a one-shot generation request. Chat history is ignored.
    """
    try:
        # For one-shot generation, explicitly ignore any provided chat history.
        request.chatid = None
        return await _dispatch_and_respond(request, client_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An internal error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.post("/api/chat")
async def chat(request: APIRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handles a conversational chat request.
    If no chatid is provided, a new chat session is created.
    """
    try:
        if request.chatid is None:
            request.chatid = await create_chat(client_id)
        return await _dispatch_and_respond(request, client_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An internal error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/api/models/{provider}")
async def get_models(provider: str):
    """
    Get available models for a specific provider.
    """
    models = HANDLERS[provider].get_models()
    if models is None:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")
    return {"models": models}


@app.post("/api/signup")
async def signup(credentials: ClientCredentials):
    """
    Create a new client.
    """
    try:
        client = await create_client(credentials)
        return {"client_id": client.id, "email": client.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email already registered")


@app.post("/api/token")
async def get_token(credentials: ClientCredentials, expr: timedelta | None = None):
    """
    Get a JWT token for a specific client_id.
    """
    client = await authenticate_client(credentials)
    if not client:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    token_expires = expr or timedelta(hours=2)
    
    token = create_token(client_id=str(client.id), expires_delta=token_expires)
    return {"access_token": token, "token_type": "bearer"}

