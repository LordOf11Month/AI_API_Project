"""
Unified AI API Server

This module implements a FastAPI-based server that provides a unified interface
for interacting with multiple AI providers (OpenAI, Google, Anthropic, DeepSeek).
The API supports both one-shot generation and conversational chat with persistent
history, user authentication, prompt templates, and API key management.

Key Features:
- Multi-provider AI model access through a unified interface
- JWT-based authentication and authorization
- Conversational chat with persistent history
- Prompt template management with variable substitution
- Per-client API key storage and management
- Streaming and non-streaming response support
- Comprehensive logging and error handling

Main Endpoints:
- /api/generate: One-shot text generation
- /api/chat: Conversational chat with history
- /api/models/{provider}: Get available models for a provider
- /api/signup: User registration
- /api/token: JWT token generation
- /api/template: Prompt template management
- /api/apikey: API key management

Dependencies:
- FastAPI: Web framework
- SQLAlchemy: Database ORM
- Pydantic: Data validation
- JWT: Token-based authentication
- Multiple AI provider SDKs

Environment Variables Required:
- GOOGLE_API_KEY: Google AI API key (optional)
- OPENAI_API_KEY: OpenAI API key (optional)
- ANTHROPIC_API_KEY: Anthropic API key (optional)
- DEEPSEEK_API_KEY: DeepSeek API key (optional)
- DATABASE_URL: Database connection string
- JWT_SECRET_KEY: Secret key for JWT token signing

Author: Ramazan Seçilmiş
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
from typing import AsyncIterable
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from app.models.DBModels import Provider
from app.routers.Dispatcher import HANDLERS, dispatch_request
from app.models.DataModels import GenerateRequest, ChatRequest, ClientCredentials, PromptTemplateCreate, message, APIKeyCreate, APIKeyUpdate
from app.DB_connection.chat_manager import create_chat, chat_history, add_message
from app.DB_connection.client_manager import create_client, authenticate_client
from app.DB_connection.PromptTemplate_manager import create_prompt_template, update_prompt_template
from app.DB_connection.api_manager import store_api_key, delete_api_key, update_api_key
from app.utils.token_utils import create_token
from app.auth.middleware import get_current_client_id
from app.utils.console_logger import info, warning, error, debug

# Load environment variables from a .env file if it exists
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager that handles startup and shutdown procedures.
    
    This function configures the database connection on startup and performs
    cleanup on shutdown. It also validates that required environment variables
    are available for AI providers.
    
    Startup Tasks:
    - Initialize database connection and verify connectivity
    - Check for provider API keys and log warnings if missing
    
    Shutdown Tasks:
    - Close database connections gracefully
    - Dispose of database engine resources
    
    Args:
        app (FastAPI): The FastAPI application instance
        
    Yields:
        None: Control back to the application during runtime
        
    Raises:
        ValueError: If database initialization fails
        Exception: If any critical startup error occurs
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
    Helper function for generate and chat endpoints to dispatch requests and format HTTP responses.
    
    This function eliminates code duplication between the /api/generate and /api/chat
    endpoints by providing a common interface for request dispatching and response
    formatting. It handles both streaming and non-streaming responses appropriately.
    
    Args:
        request (GenerateRequest): The generation request containing provider, model,
                                 messages, and other parameters
        client_id (str): The authenticated client identifier
        
    Returns:
        StreamingResponse: For streaming requests, returns a streaming HTTP response
        dict: For non-streaming requests, returns a JSON response with "response" key
        
    Raises:
        HTTPException: 
            - 500 if streaming is requested but not supported by provider
            - Any errors from the underlying dispatch_request function
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


@app.get("/api/generate")
async def generate(request: GenerateRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handle one-shot text generation requests.
    
    This endpoint provides stateless text generation using various AI providers.
    It does not maintain conversation history and treats each request independently.
    Both streaming and non-streaming responses are supported.
    
    Args:
        request (GenerateRequest): The generation request containing:
            - provider (Provider): AI provider to use (openai, google, anthropic, deepseek)
            - model (str): Specific model name to use
            - messages (list[message]): List of messages for the conversation
            - systemPrompt (SystemPrompt): System prompt with template and variables
            - parameters (dict): Provider-specific parameters (temperature, max_tokens, etc.)
            - stream (bool): Whether to stream the response
            - tools (list[Tool], optional): Function calling tools
        client_id (str): Authenticated client identifier (injected by middleware)
        
    Returns:
        StreamingResponse: For streaming requests (media-type: text/event-stream)
        dict: For non-streaming requests with format {"response": "generated_text"}
        
    Raises:
        HTTPException:
            - 400: Validation error in request parameters
            - 401: Authentication required (from middleware)
            - 500: Internal server error during generation
            
    Example:
        ```json
        {
            "provider": "openai",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello, world!"}],
            "systemPrompt": {"template_name": "default", "tenants": {}},
            "parameters": {"temperature": 0.7, "max_tokens": 150},
            "stream": false
        }
        ```
    """
    info(f"Received one-shot generation request for provider: {request.provider}", "[Generate]")
    debug(f"Model: {request.model}, Client ID: {client_id}", "[Generate]")
    
    try:
        return await _dispatch_and_respond(request, client_id)
    except ValueError as e:
        error(f"Validation error in generate endpoint: {e}", "[Generate]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Internal error in generate endpoint at line {e.__traceback__.tb_lineno}: {e}", "[Generate]")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/api/chat")
async def chat(request: ChatRequest, client_id: str = Depends(get_current_client_id)):
    """
    Handle conversational chat requests with persistent history.
    
    This endpoint manages stateful conversations by maintaining chat history in the database.
    If no chat_id is provided, a new chat session is created. The conversation history
    is automatically managed, and both user messages and AI responses are stored.
    
    Args:
        request (ChatRequest): The chat request containing:
            - provider (Provider): AI provider to use
            - model (str): Specific model name
            - message (message): New message to add to conversation
            - chat_id (UUID, optional): Existing chat session ID (creates new if None)
            - systemPrompt (SystemPrompt): System prompt configuration
            - parameters (dict): Provider-specific parameters
            - stream (bool): Whether to stream the response
            - tools (list[Tool], optional): Function calling tools
        client_id (str): Authenticated client identifier
        
    Returns:
        StreamingResponse: For streaming requests
        Response object: For non-streaming requests
        
    Side Effects:
        - Creates new chat session if chat_id is None
        - Adds user message to chat history
        - Adds AI response to chat history after generation
        
    Raises:
        HTTPException:
            - 400: Validation error in request parameters
            - 401: Authentication required
            - 500: Internal server error during chat processing
            
    Example:
        ```json
        {
            "provider": "openai",
            "model": "gpt-4",
            "message": {"role": "user", "content": "Continue our conversation"},
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "systemPrompt": {"template_name": "assistant", "tenants": {}},
            "stream": true
        }
        ```
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

            if response.type == "message":
                await add_message(request.chat_id, message(role='assistant', content=response.content))
            elif response.type == "function_call":
                await add_message(request.chat_id, message(role='assistant', content=response.function_name, function_args=response.function_args))
            elif response.type == "error":
                raise HTTPException(status_code=500, detail=response.content)
            response.chat_id = request.chat_id
            return response
    
    except ValueError as e:
        error(f"Validation error in chat endpoint: {e}", "[Chat]")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"Internal error in chat endpoint at line {e.__traceback__.tb_lineno}: {e}", "[Chat]")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/api/models/{provider}")
async def get_models(provider: str):
    """
    Retrieve available models for a specific AI provider.
    
    This endpoint returns a list of available models for the specified provider.
    The models list is fetched directly from the provider's handler and represents
    the currently available models that can be used for generation requests.
    
    Args:
        provider (str): The AI provider name (openai, google, anthropic, deepseek)
        
    Returns:
        dict: JSON response with format {"models": ["model1", "model2", ...]}
        
    Raises:
        HTTPException:
            - 400: If provider is not supported
            - 500: If provider fails to return models list
            
    Example:
        GET /api/models/openai
        Response:
        ```json
        {
            "models": [
                "gpt-4",
                "gpt-4-turbo", 
                "gpt-3.5-turbo",
                "gpt-4o"
            ]
        }
        ```
    """
    info(f"Fetching available models for provider: {provider}", "[Models]")
    provider_enum = Provider(provider.lower())
    if provider_enum not in HANDLERS:
        warning(f"Attempted to get models for unsupported provider: {provider}", "[Models]")
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")
    
    models = HANDLERS[provider_enum].get_models()
    if models is None:
        error(f"Provider '{provider}' failed to return models.", "[Models]")
        raise HTTPException(status_code=500, detail=f"Could not retrieve models for provider '{provider}'")
    
    debug(f"Returning models for provider {provider}: {models}", "[Models]")
    return {"models": models}


@app.post("/api/signup")
async def signup(credentials: ClientCredentials):
    """
    Register a new client account.
    
    This endpoint creates a new client account in the database with the provided
    email and password. The email must be unique across all clients.
    
    Args:
        credentials (ClientCredentials): Registration credentials containing:
            - email (str): Client's email address (must be unique)
            - password (str): Client's password (will be hashed before storage)
            - expr (dict, optional): Token expiration settings (not used in signup)
            
    Returns:
        dict: JSON response with format:
            ```json
            {
                "client_id": "uuid-string",
                "email": "client@example.com"
            }
            ```
            
    Raises:
        HTTPException:
            - 400: Email already registered or database integrity error
            - 500: Internal server error during account creation
            
    Example:
        ```json
        {
            "email": "user@example.com",
            "password": "secure_password123"
        }
        ```
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
        error(f"Exception during signup for {credentials.email} at line {e.__traceback__.tb_lineno}: {e}", "[Auth]")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/token")
async def get_token(credentials: ClientCredentials):
    """
    Generate a JWT access token for client authentication.
    
    This endpoint authenticates a client using email/password credentials and
    returns a JWT token that can be used for subsequent API requests. The token
    expiration can be customized through the credentials.
    
    Args:
        credentials (ClientCredentials): Authentication credentials containing:
            - email (str): Client's registered email
            - password (str): Client's password
            - expr (dict, optional): Token expiration settings as timedelta kwargs
                                   (e.g., {"hours": 24, "minutes": 30})
                                   Defaults to 2 hours if not provided
                                   
    Returns:
        dict: JSON response with format:
            ```json
            {
                "access_token": "jwt_token_string",
                "token_type": "bearer"
            }
            ```
            
    Raises:
        HTTPException:
            - 401: Incorrect email or password
            - 500: Internal server error during token generation
            
    Usage:
        1. Obtain token: GET /api/token with credentials
        2. Use token: Include "Authorization: Bearer <token>" header in requests
        
    Example:
        ```json
        {
            "email": "user@example.com", 
            "password": "secure_password123",
            "expr": {"hours": 24}
        }
        ```
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
    Create a new prompt template.
    
    This endpoint allows authenticated clients to create reusable prompt templates
    with variable substitution capabilities. Templates can include tenant fields
    that are replaced with actual values during generation requests.
    
    Args:
        template_data (PromptTemplateCreate): Template creation data containing:
            - name (str): Unique template name
            - prompt (str): Template text with {variable} placeholders
            - tenant_fields (list[str]): List of variable names used in template
        client_id (str): Authenticated client identifier
        
    Returns:
        dict: Created template information with format:
            ```json
            {
                "name": "template_name",
                "tenant_fields": ["var1", "var2"],
                "created_at": "2024-01-01T12:00:00Z"
            }
            ```
            
    Raises:
        HTTPException:
            - 401: Authentication required
            - 409: Template name already exists
            - 500: Internal server error during creation
            
    Example:
        ```json
        {
            "name": "customer_service",
            "prompt": "You are a helpful {role} assistant for {company}. Respond professionally.",
            "tenant_fields": ["role", "company"]
        }
        ```
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
        error(f"Error creating template '{template_data.name}' at line {e.__traceback__.tb_lineno}: {e}", "[Template]")
        raise HTTPException(status_code=500, detail="Failed to create template.")


@app.put("/api/template/{template_name}")
async def handle_update_template(
    template_name: str,
    template_data: PromptTemplateCreate,
    client_id: str = Depends(get_current_client_id)
):
    """
    Update an existing prompt template.
    
    This endpoint allows authenticated clients to update existing prompt templates.
    Updates create a new version of the template while preserving the original
    for backward compatibility.
    
    Args:
        template_name (str): Name of the template to update
        template_data (PromptTemplateCreate): Updated template data containing:
            - name (str): Template name (should match template_name)
            - prompt (str): Updated template text
            - tenant_fields (list[str]): Updated variable names
        client_id (str): Authenticated client identifier
        
    Returns:
        dict: Updated template information with format:
            ```json
            {
                "name": "template_name",
                "version": 2,
                "tenant_fields": ["var1", "var2"],
                "updated_at": "2024-01-01T12:00:00Z"
            }
            ```
            
    Raises:
        HTTPException:
            - 401: Authentication required
            - 404: Template not found
            - 500: Internal server error during update
            
    Example:
        PUT /api/template/customer_service
        ```json
        {
            "name": "customer_service",
            "prompt": "You are an expert {role} for {company}. Be {tone} in responses.",
            "tenant_fields": ["role", "company", "tone"]
        }
        ```
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
        error(f"Error updating template '{template_name}' at line {e.__traceback__.tb_lineno}: {e}", "[Template]")
        raise HTTPException(status_code=500, detail="Failed to update template.")


@app.post("/api/apikey", status_code=201)
async def create_api_key(
    api_key_data: APIKeyCreate,
    client_id: str = Depends(get_current_client_id)
):
    """
    Store a new API key for an AI provider.
    
    This endpoint allows authenticated clients to securely store their API keys
    for various AI providers. Keys are encrypted before storage and associated
    with the client's account for use in generation requests.
    
    Args:
        api_key_data (APIKeyCreate): API key data containing:
            - provider (Provider): AI provider (openai, google, anthropic, deepseek)
            - api_key (str): The API key to store
        client_id (str): Authenticated client identifier
        
    Returns:
        dict: Confirmation with masked key for security:
            ```json
            {
                "provider": "openai",
                "masked_api_key": "sk-1234**********************abcd",
                "message": "API key stored successfully"
            }
            ```
            
    Raises:
        HTTPException:
            - 400: Invalid provider or malformed API key
            - 401: Authentication required
            - 500: Internal server error during storage
            
    Security:
        - API keys are encrypted before database storage
        - Only masked versions are returned in responses
        - Keys are isolated per client account
        
    Example:
        ```json
        {
            "provider": "openai",
            "api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        }
        ```
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
        error(f"Error storing API key for provider '{api_key_data.provider}' at line {e.__traceback__.tb_lineno}: {e}", "[APIKey]")
        raise HTTPException(status_code=500, detail="Failed to store API key.")


# @app.get("/api/apikey/{provider}")
# async def get_api_key_endpoint(
#     provider: str,
#     client_id: str = Depends(get_current_client_id)
# ):
#     """
#     Get the API key for a specific provider. Returns masked key for security.
#     
#     This endpoint retrieves a client's stored API key for a specific provider.
#     For security purposes, only a masked version of the key is returned.
#     
#     Args:
#         provider (str): The AI provider name
#         client_id (str): Authenticated client identifier
#         
#     Returns:
#         APIKeyResponse: Masked API key information
#         
#     Raises:
#         HTTPException:
#             - 401: Authentication required  
#             - 404: No API key found for provider
#             - 500: Internal server error
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
    Update an existing API key for a provider.
    
    This endpoint allows authenticated clients to update their stored API key
    for a specific provider. The new key replaces the existing one.
    
    Args:
        provider (str): The AI provider name (openai, google, anthropic, deepseek)
        api_key_data (APIKeyUpdate): Updated API key data containing:
            - api_key (str): The new API key
            - provider (Provider): Provider enum (should match path parameter)
        client_id (str): Authenticated client identifier
        
    Returns:
        dict: Confirmation with masked key:
            ```json
            {
                "provider": "openai",
                "masked_api_key": "sk-1234**********************abcd",
                "message": "API key updated successfully"
            }
            ```
            
    Raises:
        HTTPException:
            - 400: Invalid provider or malformed API key
            - 401: Authentication required
            - 500: Internal server error during update
            
    Example:
        PUT /api/apikey/openai
        ```json
        {
            "api_key": "sk-new1234567890abcdefghijklmnopqrstuvwxyz",
            "provider": "openai"
        }
        ```
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
        error(f"Error updating API key for provider '{provider}' at line {e.__traceback__.tb_lineno}: {e}", "[APIKey]")
        raise HTTPException(status_code=500, detail="Failed to update API key.")


@app.delete("/api/apikey/{provider}")
async def delete_api_key_endpoint(
    provider: str,
    client_id: str = Depends(get_current_client_id)
):
    """
    Delete an API key for a specific provider.
    
    This endpoint allows authenticated clients to remove their stored API key
    for a specific provider. Once deleted, the client will need to use the
    system's default API keys (if available) or store a new key.
    
    Args:
        provider (str): The AI provider name (openai, google, anthropic, deepseek)
        client_id (str): Authenticated client identifier
        
    Returns:
        dict: Deletion confirmation:
            ```json
            {
                "provider": "openai",
                "message": "API key deleted successfully"
            }
            ```
            
    Raises:
        HTTPException:
            - 401: Authentication required
            - 500: Internal server error during deletion
            
    Side Effects:
        - Permanently removes the API key from storage
        - Future requests will use system default keys (if available)
        
    Example:
        DELETE /api/apikey/openai
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
        error(f"Error deleting API key for provider '{provider}' at line {e.__traceback__.tb_lineno}: {e}", "[APIKey]")
        raise HTTPException(status_code=500, detail="Failed to delete API key.")

