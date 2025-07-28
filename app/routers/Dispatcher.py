from pydantic import BaseModel, Field
from typing import Union, AsyncIterable, Dict, Any, Optional
from uuid import UUID

from app.DB_connection.PromptTemplate_manager import get_rendered_prompt
from app.handlers.GoogleHandler import GoogleHandler
from app.handlers.OpenAIHandler import OpenAIHandler
from app.handlers.AnthropicHandler import AnthropicHandler
from app.handlers.DeepseekHandler import DeepseekHandler
from jinja2  import Template

from datetime import datetime
from app.models.DataModels import RequestLog, ResponseLog, SystemPrompt, APIRequest
from app.DB_connection.request_manager import log_request, log_response, initialize_request


# A mapping of provider names to their handler classes-----------------
HANDLERS = {
    "google": GoogleHandler,
    "openai": OpenAIHandler,
    "anthropic": AnthropicHandler,
    "deepseek": DeepseekHandler,
}

#------------------------------------------------------------------------







# async def dispatch_request(request: APIRequest) -> Union[str, AsyncIterable[str]]:
#     """
#     Dispatches an API request to the appropriate handler.
#     """
#     handler_class = HANDLERS.get(request.provider.lower())

#     if not handler_class:
#         # In a FastAPI app, you'd raise an HTTPException here.
#         raise ValueError(f"Provider '{request.provider}' is not supported.")

#     system_instruction = instructionBuilder(request.systemPrompt)


#     handler_instance = handler_class(
#         model_name=request.model,
#         generation_config=request.parameters,
#         system_instruction=system_instruction
#     )

#     return await handler_instance.handle(
#         messages=chat_completion(request.chatid, request.userprompt),
#         stream=request.stream
#     )




async def dispatch_request(request: APIRequest, client_id: str):
    """
    Dispatches an API request to the appropriate handler.
    This function handles both streaming and non-streaming requests.
    """
    handler_class = HANDLERS.get(request.provider.lower())
    if not handler_class:
        raise ValueError(f"Provider '{request.provider}' is not supported.")

    # Start the request initialization but don't await it yet
    request_id_future = initialize_request(RequestLog(
        client_id=client_id,
        chat_id=request.chatid,
        user_prompt=request.userprompt,
        model_name=request.model,
        system_prompt=request.systemPrompt,
        created_at=datetime.now()
    ))

    system_instruction = get_rendered_prompt(request.systemPrompt)
    handler_instance = handler_class(
        model_name=request.model,
        generation_config=request.parameters,
        system_instruction=system_instruction
    )

    # Now await the request_id when we actually need it
    request_id = await request_id_future

    if request.stream:
        return handler_instance.stream_handle(
            user_prompt=request.userprompt,
            chat_id=request.chatid,
            request_id=request_id
        )
    else:
        return await handler_instance.sync_handle(
            user_prompt=request.userprompt,
            chat_id=request.chatid,
            request_id=request_id
        )
