from pydantic import BaseModel, Field
from typing import Union, AsyncIterable, Dict, Any, Optional
from uuid import UUID

from app.handlers.GoogleHandler import GoogleHandler
from app.handlers.OpenAIHandler import OpenAIHandler
from app.handlers.AnthropicHandler import AnthropicHandler
from app.handlers.DeepseekHandler import DeepseekHandler
from jinja2  import Template

from datetime import datetime
from app.models.DataModels import RequestLog, ResponseLog, SystemPrompt, APIRequest
from app.DB_connection.request_logger import log_request, log_response


# A mapping of provider names to their handler classes-----------------
HANDLERS = {
    "google": GoogleHandler,
    "openai": OpenAIHandler,
    "anthropic": AnthropicHandler,
    "deepseek": DeepseekHandler,
}

#------------------------------------------------------------------------


# Read root prompt
root_prompt = open("app/root_prompt.txt", "r").read()





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



def instructionBuilder(systemPrompt: SystemPrompt) -> str:
    '''
    Builds a system prompt for the chat completion request.
    '''
    pass

async def sync_request(request: APIRequest,messages:list[Dict[str, str]],request_id:UUID):
    """
    Dispatches an API request to the appropriate handler.
    """
    handler_class = HANDLERS.get(request.provider.lower())

    if not handler_class:
        # In a FastAPI app, you'd raise an HTTPException here.
        raise ValueError(f"Provider '{request.provider}' is not supported.")

    system_instruction = instructionBuilder(request.systemPrompt)


    handler_instance = handler_class(
        model_name=request.model,
        generation_config=request.parameters,
        system_instruction=system_instruction
    )

    return await handler_instance.sync_handle(
        messages=messages,
        request_id=request_id
    )



async def stream_request(request: APIRequest,messages:list[Dict[str, str]]):
    '''
    Handles a stream request
    '''
    pass
