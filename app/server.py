from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
import google.generativeai as genai
from typing import AsyncIterable
from contextlib import asynccontextmanager

from app.routers.Dispacther import dispatch_request, APIRequest
from app.handlers.GoogleHandler import GoogleHandler
from app.handlers.OpenAIHandler import OpenAIHandler

# Load environment variables from a .env file if it exists
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Configure clients on startup.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        genai.configure(api_key=google_api_key)
    else:
        print("Warning: GOOGLE_API_KEY environment variable not set.")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Warning: OPENAI_API_KEY environment variable not set.")
        
    yield
    # Add any cleanup code here, to be run on shutdown.





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
        response = await dispatch_request(request)
        
        if request.stream:
            # Ensure the response is an async iterable, as expected for streaming
            if isinstance(response, AsyncIterable):
                return StreamingResponse(response, media_type="text/event-stream")
            else:
                # This could happen if a handler fails to return a stream correctly.
                raise HTTPException(status_code=500, detail="Streaming was requested but is not supported or failed for this provider.")
        else:
            # For non-streaming requests, return the complete response in a JSON object.
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
    if provider.lower() == "google":
        return {"models": GoogleHandler.get_models()}
    elif provider.lower() == "openai":
        return {"models": OpenAIHandler.get_models()}
    else:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")
