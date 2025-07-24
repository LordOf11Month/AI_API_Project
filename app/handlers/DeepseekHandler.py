import os
from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler


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

    async def handle(self, prompt: str, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """
        Processes a prompt and returns the model's response.
        """
        messages = []
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=stream,
                **self.generation_config
            )
            if stream:
                async def stream_generator():
                    async for chunk in response:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                return stream_generator()
            else:
                return response.choices[0].message.content
        except Exception as e:
            print(f"Error handling Deepseek request: {e}")
            return f"An error occurred: {e}"


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