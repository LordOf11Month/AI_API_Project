from typing import Union, AsyncIterable, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.logging.request_logger import log_response


class AnthropicHandler(BaseHandler):
    """
    Handler for Anthropic's Claude models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncAnthropic()

    async def sync_handle(self, messages: list[Dict[str, str]], request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                system=self.system_instruction,
                **self.generation_config
            )
            asyncio.create_task(log_response(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                response=response.content[0].text,
                status=response.stop_reason == "end_turn",
            )))
            return response
        except Exception as e:
            print(f"Error handling Anthropic request: {e}")
            return f"An error occurred: {e}"

    async def stream_handle(self, messages: list[Dict[str, str]]) -> AsyncIterable[Dict[str, Any]]:
        """
        Processes a prompt and returns the model's response as an async iterable of strings.
        """
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                system=self.system_instruction,
                **self.generation_config,
                stream=True
            )
            async for chunk in response:
                yield chunk
        except Exception as e:
            print(f"Error handling Anthropic request: {e}")
            yield f"An error occurred: {e}"

    @staticmethod
    def get_models() -> list[str]:
        """`
        Get a list of available Anthropic models.
        """
        try:
            # Note: Anthropic SDK doesn't have a direct equivalent of OpenAI's `models.list()`.
            # Officially, they recommend referring to their documentation for model names.
            # For this reason, we'll return a static list of commonly used models.
            # You can update this list as new models are released.
            return [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
        except Exception as e:
            print(f"Error getting Anthropic models: {e}")
            return []
        