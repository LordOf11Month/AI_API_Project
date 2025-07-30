
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
from typing import AsyncIterable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.routers.Dispatcher import HANDLERS, dispatch_request
from app.models.DataModels import APIRequest, ClientCredentials, PromptTemplateCreate
from app.DB_connection.chat_manager import create_chat
from app.DB_connection.client_manager import create_client, authenticate_client
from app.DB_connection.PromptTemplate_manager import create_prompt_template, update_prompt_template
from app.auth.token_utils import create_token
from app.auth.middleware import get_current_client_id
from app.utils.console_logger import info, warning, error, debug

# Load environment variables from a .env file if it exists
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Configure clients on startup.
    """
    info("Starting application lifespan", "[Lifespan]")
    # Initialize database first as other services might depend on it
    try:
        from app.DB_connection.database import db_manager
        info("Initializing database connection...", "[DB]")
        # Access engine to trigger initialization
        if db_manager.engine is None:
            raise ValueError("Failed to initialize database connection")
        info("Database connection established successfully", "[DB]")
    except Exception as e:
        error(f"Error initializing database: {e}", "[DB]")
        raise

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        warning("GOOGLE_API_KEY environment variable not set.", "[Config]")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        warning("OPENAI_API_KEY environment variable not set.", "[Config]")

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        warning("ANTHROPIC_API_KEY environment variable not set.", "[Config]")
        
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        warning("DEEPSEEK_API_KEY environment variable not set.", "[Config]")
        
    yield
    
    # Cleanup on shutdown
    info("Closing database connections...", "[Lifespan]")
    if db_manager.engine:
        await db_manager.engine.dispose()
    info("Database connections closed", "[Lifespan]")


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
    debug(f"Dispatching request for client: {client_id}", "[Server]")
    
    response = await dispatch_request(request, client_id)
    
    if request.stream:
        if isinstance(response, AsyncIterable):
            debug("Streaming response initiated", "[Server]")
            return StreamingResponse(response, media_type="text/event-stream")
        else:
            error("Streaming was requested but is not supported or failed for this provider.", "[Server]")
            raise HTTPException(status_code=500, detail="Streaming was requested but is not supported or failed for this provider.")
    else:
        debug("Returning non-streamed response", "[Server]")
        return {"response": response}


@app.post("/api/generate")
async def generate(request: APIRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handles a one-shot generation request. Chat history is ignored.
    """
    info(f"Received one-shot generation request for provider: {request.provider}", "[Generate]")
    debug(f"Model: {request.model}, Client ID: {client_id}", "[Generate]")
    
    try:
        # For one-shot generation, explicitly ignore any provided chat history.
        request.chatid = None
        return await _dispatch_and_respond(request, client_id)
    except ValueError as e:
        error(f"Validation error in generate endpoint: {e}", "[Generate]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Internal error in generate endpoint: {e}", "[Generate]")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.post("/api/chat")
async def chat(request: APIRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handles a conversational chat request.
    If no chatid is provided, a new chat session is created.
    """
    info(f"Received chat request for provider: {request.provider}", "[Chat]")
    debug(f"Model: {request.model}, Client ID: {client_id}, Chat ID: {request.chatid}", "[Chat]")
    
    try:
        if request.chatid is None:
            info("No chat ID provided, creating a new chat session.", "[Chat]")
            request.chatid = await create_chat(client_id)
            info(f"New chat session created with ID: {request.chatid}", "[Chat]")
        return await _dispatch_and_respond(request, client_id)
    except ValueError as e:
        error(f"Validation error in chat endpoint: {e}", "[Chat]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Internal error in chat endpoint: {e}", "[Chat]")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/api/models/{provider}")
async def get_models(provider: str):
    """
    Get available models for a specific provider.
    """
    info(f"Fetching available models for provider: {provider}", "[Models]")
    if provider not in HANDLERS:
        warning(f"Attempted to get models for unsupported provider: {provider}", "[Models]")
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")
    
    models = HANDLERS[provider].get_models()
    if models is None:
        error(f"Provider '{provider}' failed to return models.", "[Models]")
        raise HTTPException(status_code=500, detail=f"Could not retrieve models for provider '{provider}'")
    
    debug(f"Returning models for provider {provider}: {models}", "[Models]")
    return {"models": models}


@app.post("/api/signup")
async def signup(credentials: ClientCredentials):
    """
    Create a new client.
    """
    info(f"New client signup attempt for email: {credentials.email}", "[Auth]")
    try:
        client = await create_client(credentials)
        info(f"Client created successfully for email: {client.email}", "[Auth]")
        return {"client_id": client.id, "email": client.email}
    except IntegrityError as e:
        if "unique constraint" in str(e.orig).lower():
            warning(f"Signup failed for email {credentials.email}: already registered.", "[Auth]")
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            error(f"Database integrity error during signup for {credentials.email}: {e}", "[Auth]")
            raise HTTPException(status_code=400, detail="Database error")
    except Exception as e:
        error(f"Exception during signup for {credentials.email}: {e}", "[Auth]")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/token")
async def get_token(credentials: ClientCredentials, expr: timedelta | None = None):
    """
    Get a JWT token for a specific client_id.
    """
    info(f"Token requested for email: {credentials.email}", "[Auth]")
    client = await authenticate_client(credentials)
    if not client:
        warning(f"Failed authentication attempt for email: {credentials.email}", "[Auth]")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    token_expires = expr or timedelta(hours=2)
    
    token = create_token(client_id=str(client.id), expires_delta=token_expires)
    info(f"Token generated for client: {client.id}", "[Auth]")
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/template", status_code=201)
async def handle_create_template(
    template_data: PromptTemplateCreate,
    client_id: str = Depends(get_current_client_id)
):
    """
    Create a new prompt template. Requires authentication.
    """
    info(f"Creating new prompt template '{template_data.name}' for client: {client_id}", "[Template]")
    try:
        template = await create_prompt_template(template_data)
        info(f"Template '{template.name}' created successfully with ID: {template.id}", "[Template]")
        return {
            "id": template.id,
            "name": template.name,
            "version": template.version,
            "tenant_fields": template.tenant_fields,
            "created_at": template.created_at
        }
    except ValueError as e:
        warning(f"Conflict creating template '{template_data.name}': {e}", "[Template]")
        raise HTTPException(status_code=409, detail=str(e)) # 409 Conflict
    except Exception as e:
        error(f"Error creating template '{template_data.name}': {e}", "[Template]")
        raise HTTPException(status_code=500, detail="Failed to create template.")


@app.put("/api/template/{template_name}")
async def handle_update_template(
    template_name: str,
    template_data: PromptTemplateCreate,
    client_id: str = Depends(get_current_client_id)
):
    """
    Update an existing prompt template. Requires authentication.
    """
    info(f"Updating prompt template '{template_name}' for client: {client_id}", "[Template]")
    try:
        template = await update_prompt_template(template_name, template_data)
        info(f"Template '{template_name}' updated successfully to version {template.version}", "[Template]")
        return {
            "id": template.id,
            "name": template.name,
            "version": template.version,
            "tenant_fields": template.tenant_fields,
            "updated_at": template.updated_at
        }
    except ValueError as e:
        warning(f"Template '{template_name}' not found for update: {e}", "[Template]")
        raise HTTPException(status_code=404, detail=str(e)) # 404 Not Found
    except Exception as e:
        error(f"Error updating template '{template_name}': {e}", "[Template]")
        raise HTTPException(status_code=500, detail="Failed to update template.")

