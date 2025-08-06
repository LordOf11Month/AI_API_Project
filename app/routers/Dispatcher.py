"""
Request Dispatcher Module

This module implements the core request dispatching functionality for the Unified AI API.
It serves as the central routing system that directs generation requests to the appropriate
AI provider handlers while managing request lifecycle, prompt template rendering, and
API key retrieval.

Key Responsibilities:
- Route requests to provider-specific handlers (OpenAI, Google, Anthropic, DeepSeek)
- Manage request initialization and tracking in the database
- Handle prompt template rendering with variable substitution
- Retrieve and manage client-specific or system-wide API keys
- Support both streaming and non-streaming response modes
- Provide unified interface regardless of underlying provider differences

Architecture:
The dispatcher follows a handler pattern where each AI provider has a dedicated
handler class that implements the BaseHandler interface. This allows for:
- Consistent API across different providers
- Provider-specific optimizations and configurations
- Easy addition of new providers
- Centralized request management and logging

Workflow:
1. Receive GenerateRequest from API endpoint
2. Validate and retrieve appropriate handler for provider
3. Initialize request tracking in database
4. Retrieve client API key or fall back to system key
5. Render prompt template with variable substitution
6. Create handler instance with configuration
7. Route to streaming or non-streaming handler method
8. Return response to calling endpoint

Author: Ramazan Seçilmiş
Version: 1.0.0
"""

from datetime import datetime
from app.DB_connection.PromptTemplate_manager import get_rendered_prompt
from app.handlers.GoogleHandler import GoogleHandler
from app.handlers.OpenAIHandler import OpenAIHandler
from app.handlers.AnthropicHandler import AnthropicHandler
from app.handlers.DeepseekHandler import DeepseekHandler
from app.models.DataModels import RequestInit, GenerateRequest
from app.models.DBModels import Provider
from app.DB_connection.request_manager import initialize_request
from app.utils.console_logger import info, error, debug
from app.DB_connection.api_manager import get_api_key

# A mapping of provider enum to their handler classes
HANDLERS = {
    Provider.google: GoogleHandler,
    Provider.openai: OpenAIHandler,
    Provider.anthropic: AnthropicHandler,
    Provider.deepseek: DeepseekHandler,
}

async def dispatch_request(request: GenerateRequest, client_id: str):
    """
    Dispatch an AI generation request to the appropriate provider handler.
    
    This is the main entry point for all AI generation requests in the system.
    It orchestrates the entire request lifecycle from validation through response
    generation, handling both streaming and non-streaming modes. The function
    provides a unified interface regardless of the underlying AI provider.
    
    Request Processing Workflow:
    1. Validate provider and retrieve handler class
    2. Retrieve client-specific or system API key
    3. Initialize request tracking in database for analytics/billing
    4. Render prompt template with variable substitution
    5. Create configured handler instance for the provider
    6. Route to appropriate handler method (streaming/non-streaming)
    7. Return response to calling endpoint
    
    Args:
        request (GenerateRequest): The generation request containing:
            - provider (Provider): AI provider enum (google, openai, anthropic, deepseek)
            - model (str): Specific model name to use
            - messages (list[message]): Conversation messages for generation
            - systemPrompt (SystemPrompt): System prompt with template and variables
            - parameters (dict): Provider-specific generation parameters
            - stream (bool): Whether to stream the response
            - tools (list[Tool], optional): Function calling tools for the model
        client_id (str): Authenticated client identifier for API key retrieval
                        and request tracking
    
    Returns:
        Union[AsyncIterable[bytes], str, dict]: Response format depends on stream parameter:
            - For streaming: AsyncIterable[bytes] yielding response chunks
            - For non-streaming: str or dict containing the complete response
    
    Raises:
        ValueError: If the specified provider is not supported or not found in HANDLERS
        Exception: Any errors from handler initialization, API key retrieval, 
                  prompt rendering, or generation process
    
    Database Side Effects:
        - Creates a new request record for tracking and analytics
        - Records request metadata (client_id, model, provider, timestamp)
        - Handler methods will update request with completion status and tokens
    
    Example Usage:
        ```python
        request = GenerateRequest(
            provider=Provider.openai,
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            systemPrompt={"template_name": "default", "tenants": {}},
            stream=False
        )
        response = await dispatch_request(request, "client-uuid")
        ```
    
    Note:
        This function handles provider-agnostic logic. Provider-specific
        behavior is implemented in individual handler classes that inherit
        from BaseHandler and implement sync_handle() and stream_handle() methods.
    """
    info(f"Dispatching request for provider: {request.provider.value}", "[Dispatcher]")
    debug(f"Client ID: {client_id}, Model: {request.model}", "[Dispatcher]")
    
    handler_class = HANDLERS.get(request.provider)
    if not handler_class:
        error(f"Provider '{request.provider.value}' not found in handlers", "[Dispatcher]")
        raise ValueError(f"Provider '{request.provider.value}' is not supported.")

    debug(f"Found handler class: {handler_class.__name__}", "[Dispatcher]")

    api_key, is_client_api = await get_api_key(request.provider.value, client_id)

    # Initialize the request and await it immediately
    debug("Initializing request in database...", "[Dispatcher]")
    request_id = await initialize_request(RequestInit(
        client_id=client_id,
        model_name=request.model,
        provider=request.provider,
        is_client_api=is_client_api,
        created_at=datetime.now()
    ))
    info(f"Request initialized with ID: {request_id}", "[Dispatcher]")

    # Get the rendered prompt and await it
    debug("Getting rendered prompt...", "[Dispatcher]")
    system_instruction = await get_rendered_prompt(request.systemPrompt)
    debug(f"Rendered system instruction (first 100 chars): {str(system_instruction)[:100]}...", "[Dispatcher]")
    
    debug("Creating handler instance...", "[Dispatcher]")
    handler_instance = handler_class(
        model_name=request.model,
        generation_config=request.parameters,
        system_instruction=system_instruction,
        API_KEY=api_key
    )
    debug(f"Handler instance created: {type(handler_instance).__name__}", "[Dispatcher]")

    if request.stream:
        info("Calling stream_handle for streaming response", "[Dispatcher]")
        return handler_instance.stream_handle(
            messages=request.messages,
            request_id=request_id,
            tools=request.tools
        )
    else:
        info("Calling sync_handle for non-streaming response", "[Dispatcher]")
        result = await handler_instance.sync_handle(
            messages=request.messages,
            request_id=request_id,
            tools=request.tools
        )
        debug(f"Handler returned result of type {type(result)}", "[Dispatcher]")
        return result
