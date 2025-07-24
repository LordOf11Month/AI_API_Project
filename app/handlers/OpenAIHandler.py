from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.logging.request_logger import log_response


class OpenAIHandler(BaseHandler):
    """
    Handler for OpenAI's GPT models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncOpenAI()

    async def sync_handle(self, messages: list[Dict[str, str]], request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})


        try:
            # Note: The 'chat.completions' endpoint is the current standard for all modern
            # OpenAI models (e.g., GPT-4, GPT-4o), even for single-turn, non-chat requests.
            # This is the recommended approach by OpenAI for accessing their latest models.
            #thats why I use this endpoint
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **self.generation_config
            )
            asyncio.create_task(log_response(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                response=response.choices[0].message.content,
                status=response.choices[0].finish_reason == "stop",
            )))
            return response
        except Exception as e:
            print(f"Error handling OpenAI request: {e}")
            return f"An error occurred: {e}"
        
    async def stream_handle(self, messages: list[Dict[str, str]]) -> AsyncIterable[Dict[str, Any]]:
        '''
        Processes a prompt and returns the model's response as an async iterable of strings.
        '''
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **self.generation_config,
                stream=True
            )
            async for chunk in response:
                yield chunk
        except Exception as e:
            print(f"Error handling OpenAI request: {e}")
            yield f"An error occurred: {e}"


    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available OpenAI models. 
        This is a static method so it can be called without creating an instance.
        """
        try:
            client = OpenAI()
            return [model.id for model in client.models.list()]
        except Exception as e:
            print(f"Error getting OpenAI models: {e}")
            return []
    
    