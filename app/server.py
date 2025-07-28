from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
import google.generativeai as genai
from typing import AsyncIterable, Dict, List
from contextlib import asynccontextmanager
from datetime import datetime

from app.routers.Dispatcher import HANDLERS, stream_request, sync_request
from app.DB_connection.chat_compiler import chat_complier
from app.models.DataModels import APIRequest, RequestLog
from app.DB_connection.request_logger import initialize_request

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


@app.post("/api/generate")
async def generate(request: APIRequest):
    """
    Handles a generation request by dispatching it to the correct provider handler.
    It supports both streaming and non-streaming responses.
    """
    try:
        messages: List[Dict[str, str]] = []
        messages.append({"role": "user", "content": request.userprompt})

        request_id = await initialize_request(RequestLog(
            chat_id=request.chatid,
            user_prompt=request.userprompt,
            model_name=request.model,
            system_prompt=request.systemPrompt,
            created_at=datetime.now()
        ))
        
        if request.stream:
            response = await stream_request(request)
            # Ensure the response is an async iterable, as expected for streaming
            if isinstance(response, AsyncIterable):
                return StreamingResponse(response, media_type="text/event-stream")
            else:
                # This could happen if a handler fails to return a stream correctly.
                raise HTTPException(status_code=500, detail="Streaming was requested but is not supported or failed for this provider.")
        else:
            response = await sync_request(request,messages,request_id)
            # For non-streaming requests, return the complete response in a JSON object.
            return {"response": response}

    except ValueError as e:
        # Catches unsupported provider errors from the dispatcher
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # A general catch-all for other unexpected errors during the process
        print(f"An internal error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.post("/api/chat")
async def chat(request: APIRequest):
    """
    Handles a chat request by dispatching it to the correct provider handler.
    """
    try:
        # Initialize messages list with the user prompt
        messages: List[Dict[str, str]] = []
        await chat_complier(request.chatid, messages, request.provider,request.userprompt)

        request_id = await initialize_request(RequestLog(
            chat_id=request.chatid,
            user_prompt=request.userprompt,
            model_name=request.model,
            system_prompt=request.systemPrompt,
            created_at=datetime.now()
        ))

        if request.stream:
            response = await stream_request(request, messages)
            if isinstance(response, AsyncIterable):
                return StreamingResponse(response, media_type="text/event-stream")
            else:
                # This could happen if a handler fails to return a stream correctly.
                raise HTTPException(status_code=500, detail="Streaming was requested but is not supported or failed for this provider.")
        else:
            response = await sync_request(request, messages, request_id)
            return {"response": response}
    except ValueError as e:
        # Catches unsupported provider errors from the dispatcher
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # A general catch-all for other unexpected errors during the process
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

