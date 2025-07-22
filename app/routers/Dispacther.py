from pydantic import BaseModel, Field
from typing import Union, AsyncIterable, Dict, Any, Optional

from app.handlers.GoogleHandler import GoogleHandler
from app.handlers.OpenAIHandler import OpenAIHandler
from app.handlers.AnthropicHandler import AnthropicHandler



# A mapping of provider names to their handler classes-----------------
HANDLERS = {
    "google": GoogleHandler,
    "openai": OpenAIHandler,
    "anthropic": AnthropicHandler,
}

#------------------------------------------------------------------------


# Read root prompt
root_prompt = open("app/root_prompt.txt", "r").read()

# Pydantic model for your API request
class APIRequest(BaseModel):
    provider: str
    model: str
    stream: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)
    clientSystemPrompt: Optional[str] = None
    userPrompt: str





async def dispatch_request(request: APIRequest) -> Union[str, AsyncIterable[str]]:
    """
    Dispatches an API request to the appropriate handler.
    """
    handler_class = HANDLERS.get(request.provider.lower())

    if not handler_class:
        # In a FastAPI app, you'd raise an HTTPException here.
        raise ValueError(f"Provider '{request.provider}' is not supported.")

    if request.clientSystemPrompt:
        system_instruction = root_prompt + "[ " + request.clientSystemPrompt + " ]"
    else:
        system_instruction = root_prompt

    handler_instance = handler_class(
        model_name=request.model,
        generation_config=request.parameters,
        system_instruction=system_instruction
    )

    return await handler_instance.handle(
        prompt=request.userPrompt,
        stream=request.stream
    )
