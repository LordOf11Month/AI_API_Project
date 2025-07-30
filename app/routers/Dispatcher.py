from pydantic import BaseModel, Field
from typing import Union, AsyncIterable, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.DB_connection.PromptTemplate_manager import get_rendered_prompt
from app.handlers.GoogleHandler import GoogleHandler
from app.handlers.OpenAIHandler import OpenAIHandler
from app.handlers.AnthropicHandler import AnthropicHandler
from app.handlers.DeepseekHandler import DeepseekHandler
from app.models.DataModels import RequestLog, ResponseLog, SystemPrompt, APIRequest
from app.DB_connection.request_manager import initialize_request
from app.utils.debug_logger import debug_log

# A mapping of provider names to their handler classes
HANDLERS = {
    "google": GoogleHandler,
    "openai": OpenAIHandler,
    "anthropic": AnthropicHandler,
    "deepseek": DeepseekHandler,
}

async def dispatch_request(request: APIRequest, client_id: str):
    """
    Dispatches an API request to the appropriate handler.
    This function handles both streaming and non-streaming requests.
    """
    debug_log(f"Starting dispatch_request for provider: {request.provider}", "[Dispatcher]")
    debug_log(f"Client ID: {client_id}", "[Dispatcher]")
    debug_log(f"Request model: {request.model}", "[Dispatcher]")
    
    handler_class = HANDLERS.get(request.provider.lower())
    if not handler_class:
        debug_log(f"ERROR: Provider '{request.provider}' not found in handlers", "[Dispatcher]")
        raise ValueError(f"Provider '{request.provider}' is not supported.")

    debug_log(f"Found handler class: {handler_class.__name__}", "[Dispatcher]")

    # Initialize the request and await it immediately
    debug_log("Initializing request in database...", "[Dispatcher]")
    request_id = await initialize_request(RequestLog(
        client_id=client_id,
        chat_id=request.chatid,
        user_prompt=request.userprompt,
        model_name=request.model,
        system_prompt=request.systemPrompt,
        created_at=datetime.now()
    ))
    debug_log(f"Request initialized with ID: {request_id}", "[Dispatcher]")

    # Get the rendered prompt and await it
    debug_log("Getting rendered prompt...", "[Dispatcher]")
    system_instruction = await get_rendered_prompt(request.systemPrompt)
    debug_log(f"Rendered system instruction: {system_instruction[:100]}...", "[Dispatcher]")
    
    debug_log("Creating handler instance...", "[Dispatcher]")
    handler_instance = handler_class(
        model_name=request.model,
        generation_config=request.parameters,
        system_instruction=system_instruction
    )
    debug_log(f"Handler instance created: {type(handler_instance).__name__}", "[Dispatcher]")

    if request.stream:
        debug_log("Calling stream_handle...", "[Dispatcher]")
        return handler_instance.stream_handle(
            user_prompt=request.userprompt,
            chat_id=request.chatid,
            request_id=request_id
        )
    else:
        debug_log("Calling sync_handle...", "[Dispatcher]")
        result = await handler_instance.sync_handle(
            user_prompt=request.userprompt,
            chat_id=request.chatid,
            request_id=request_id
        )
        debug_log(f"Handler returned: {type(result)} - {str(result)[:100]}...", "[Dispatcher]")
        return result
