import os
from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.logging.request_logger import log_response


class DeepseekHandler(BaseHandler):
    """
    Handler for Deepseek models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncOpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )

    async def sync_handle(self, messages: list[Dict[str, str]], request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})

        try:
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
            print(f"Error handling Deepseek request: {e}")
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
            print(f"Error handling Deepseek request: {e}")
            yield f"An error occurred: {e}"


    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available Deepseek models. 
        This is a static method so it can be called without creating an instance.
        """
        try:
            client = OpenAI(
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com/v1"
            )
            return [model.id for model in client.models.list()]
        except Exception as e:
            print(f"Error getting Deepseek models: {e}, returning default list")
            return ["deepseek-chat", "deepseek-coder"] 