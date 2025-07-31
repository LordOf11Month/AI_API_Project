
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
from typing import AsyncIterable
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from app.routers.Dispatcher import HANDLERS, dispatch_request
from app.models.DataModels import GenerateRequest, ChatRequest, ClientCredentials, PromptTemplateCreate, message, APIKeyCreate, APIKeyUpdate
from app.DB_connection.chat_manager import create_chat, chat_history, add_message
from app.DB_connection.client_manager import create_client, authenticate_client
from app.DB_connection.PromptTemplate_manager import create_prompt_template, update_prompt_template
from app.DB_connection.api_manager import store_api_key, delete_api_key, update_api_key
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

    global isAdvanced
    isAdvanced = os.getenv('ADVENCE_LOGING_ENABLED', 'false').lower() == 'true'
    if isAdvanced:
        warning("Advanced logging enabled", "[Config]")
    else:
        warning("Advanced logging disabled", "[Config]")


    # Check if all provider API keys are set
    if not os.getenv("GOOGLE_API_KEY"):
        warning("GOOGLE_API_KEY environment variable not set.", "[Config]")

    if not os.getenv("OPENAI_API_KEY"):
        warning("OPENAI_API_KEY environment variable not set.", "[Config]")

    if not os.getenv("ANTHROPIC_API_KEY"):
        warning("ANTHROPIC_API_KEY environment variable not set.", "[Config]")
        
    if not os.getenv("DEEPSEEK_API_KEY"):
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


async def _dispatch_and_respond(request: GenerateRequest, client_id: str):
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
async def generate(request: GenerateRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handles a one-shot generation request. Chat history is ignored.
    """
    info(f"Received one-shot generation request for provider: {request.provider}", "[Generate]")
    debug(f"Model: {request.model}, Client ID: {client_id}", "[Generate]")
    
    try:
        return await _dispatch_and_respond(request, client_id)
    except ValueError as e:
        error(f"Validation error in generate endpoint: {e}", "[Generate]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Internal error in generate endpoint: {e}", "[Generate]")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.post("/api/chat")
async def chat(request: ChatRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handles a conversational chat request.
    If no chatid is provided, a new chat session is created.
    """
    
    
    info(f"Received chat request for provider: {request.provider}", "[Chat]")
    debug(f"Model: {request.model}, Client ID: {client_id}, Chat ID: {request.chat_id}", "[Chat]")
    
    try:
        messages = []
        if request.chat_id is None:
            info("No chat ID provided, creating a new chat session.", "[Chat]")
            request.chat_id = await create_chat(client_id)
            info(f"New chat session created with ID: {request.chat_id}", "[Chat]")
            await add_message(request.chat_id, request.message)
        else:
            info(f"Using existing chat session with ID: {request.chat_id}", "[Chat]")
            messages = await chat_history(request.chat_id)
            await add_message(request.chat_id, request.message)
        messages.append(request.message)



        response = await _dispatch_and_respond(
            GenerateRequest(provider=request.provider, 
                            model=request.model, 
                            systemPrompt=request.systemPrompt, 
                            stream=request.stream,
                            parameters=request.parameters,
                            messages=messages), client_id)
        
        if request.stream:
            # For streaming responses, we need to collect chunks and save after streaming
            async def stream_and_save():
                complete_response = []
                async for chunk in response.body_iterator:
                    complete_response.append(chunk.decode())
                    yield chunk
                # After streaming, save the complete response to database
                full_response = ''.join(complete_response)
                await add_message(request.chat_id, message(role='assistant', content=full_response))
            
            return StreamingResponse(stream_and_save(), media_type="text/event-stream")
        else:
            # For non-streaming responses, save directly and return
            # Handle both string responses and dict responses from handlers
            if isinstance(response, dict) and "response" in response:
                content = response["response"]
            else:
                content = response
            
            await add_message(request.chat_id, message(role='assistant', content=content))
            return response,request.chat_id
    
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
async def get_token(credentials: ClientCredentials):
    """
    Get a JWT token for a specific client_id.
    """
    info(f"Token requested for email: {credentials.email}", "[Auth]")
    client = await authenticate_client(credentials)
    if not client:
        warning(f"Failed authentication attempt for email: {credentials.email}", "[Auth]")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if credentials.expr is None:
        token_expires = timedelta(hours=2)
    else:
        token_expires = timedelta(**credentials.expr)  # Unpack dict into timedelta
    
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
        info(f"Template '{template.name}' created successfully", "[Template]")
        return {
            "name": template.name,
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


@app.post("/api/apikey", status_code=201)
async def create_api_key(
    api_key_data: APIKeyCreate,
    client_id: str = Depends(get_current_client_id)
):
    """
    Store/create a new API key for a provider. Requires authentication.
    """
    info(f"Creating API key for provider: {api_key_data.provider} for client: {client_id}", "[APIKey]")
    try:
        await store_api_key(api_key_data.provider.value, client_id, api_key_data.api_key)
        info(f"API key for provider '{api_key_data.provider}' stored successfully", "[APIKey]")
        
        # Return masked API key for security
        masked_key = api_key_data.api_key[:8] + "*" * (len(api_key_data.api_key) - 12) + api_key_data.api_key[-4:]
        return {
            "provider": api_key_data.provider,
            "masked_api_key": masked_key,
            "message": "API key stored successfully"
        }
    except ValueError as e:
        warning(f"Invalid data for API key creation: {e}", "[APIKey]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Error storing API key for provider '{api_key_data.provider}': {e}", "[APIKey]")
        raise HTTPException(status_code=500, detail="Failed to store API key.")


# @app.get("/api/apikey/{provider}")
# async def get_api_key_endpoint(
#     provider: str,
#     client_id: str = Depends(get_current_client_id)
# ):
#     """
#     Get the API key for a specific provider. Returns masked key for security.
#     """
#     info(f"Retrieving API key for provider: {provider} for client: {client_id}", "[APIKey]")
#     try:
#         api_key = await get_api_key(provider, client_id)
#         if not api_key:
#             warning(f"No API key found for provider '{provider}' and client: {client_id}", "[APIKey]")
#             raise HTTPException(status_code=404, detail=f"No API key found for provider '{provider}'")
        
#         # Return masked API key for security
#         masked_key = api_key[:8] + "*" * (len(api_key) - 12) + api_key[-4:]
#         debug(f"API key retrieved for provider {provider}", "[APIKey]")
#         return APIKeyResponse(
#             provider=provider,
#             masked_api_key=masked_key
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         error(f"Error retrieving API key for provider '{provider}': {e}", "[APIKey]")
#         raise HTTPException(status_code=500, detail="Failed to retrieve API key.")


@app.put("/api/apikey/{provider}")
async def update_api_key_endpoint(
    provider: str,
    api_key_data: APIKeyUpdate,
    client_id: str = Depends(get_current_client_id)
):
    """
    Update an existing API key for a provider. Requires authentication.
    """
    info(f"Updating API key for provider: {provider} for client: {client_id}", "[APIKey]")
    try:
        await update_api_key(provider, client_id, api_key_data.api_key)
        info(f"API key for provider '{provider}' updated successfully", "[APIKey]")
        
        # Return masked API key for security
        masked_key = api_key_data.api_key[:8] + "*" * (len(api_key_data.api_key) - 12) + api_key_data.api_key[-4:]
        return {
            "provider": provider,
            "masked_api_key": masked_key,
            "message": "API key updated successfully"
        }
    except ValueError as e:
        warning(f"Invalid data for API key update: {e}", "[APIKey]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Error updating API key for provider '{provider}': {e}", "[APIKey]")
        raise HTTPException(status_code=500, detail="Failed to update API key.")


@app.delete("/api/apikey/{provider}")
async def delete_api_key_endpoint(
    provider: str,
    client_id: str = Depends(get_current_client_id)
):
    """
    Delete an API key for a specific provider. Requires authentication.
    """
    info(f"Deleting API key for provider: {provider} for client: {client_id}", "[APIKey]")
    try:
        await delete_api_key(provider, client_id)
        info(f"API key for provider '{provider}' deleted successfully", "[APIKey]")
        return {
            "provider": provider,
            "message": "API key deleted successfully"
        }
    except Exception as e:
        error(f"Error deleting API key for provider '{provider}': {e}", "[APIKey]")
        raise HTTPException(status_code=500, detail="Failed to delete API key.")

