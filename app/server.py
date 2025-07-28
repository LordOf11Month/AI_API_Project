from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
import google.generativeai as genai
from typing import AsyncIterable, Dict, List
from contextlib import asynccontextmanager
from datetime import datetime

from app.routers.Dispatcher import HANDLERS, stream_request, sync_request

from app.models.DataModels import APIRequest, RequestLog
from app.DB_connection.request_logger import initialize_request
from app.DB_connection.chat_manager import create_chat

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


async def _dispatch_and_respond(request: APIRequest):
    """
    Helper function to dispatch a request and format the HTTP response.
    """
    response = await dispatch_request(request)
    
    if request.stream:
        if isinstance(response, AsyncIterable):
            return StreamingResponse(response, media_type="text/event-stream")
        else:
            raise HTTPException(status_code=500, detail="Streaming was requested but is not supported or failed for this provider.")
    else:
        return {"response": response}


@app.post("/api/generate")
async def generate(request: APIRequest):
    """
    Handles a one-shot generation request. Chat history is ignored.
    """
    try:
        # For one-shot generation, explicitly ignore any provided chat history.
        request.chatid = None
        return await _dispatch_and_respond(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An internal error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.post("/api/chat")
async def chat(request: APIRequest):
    """
    Handles a conversational chat request.
    If no chatid is provided, a new chat session is created.
    """
    try:
        if request.chatid is None:
            request.chatid = await create_chat()
        return await _dispatch_and_respond(request)
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

