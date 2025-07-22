from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler


class OpenAIHandler(BaseHandler):
    """
    Handler for OpenAI's GPT models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncOpenAI()

    async def handle(self, prompt: str, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """
        Processes a prompt and returns the model's response.
        """
        messages = []
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            # Note: The 'chat.completions' endpoint is the current standard for all modern
            # OpenAI models (e.g., GPT-4, GPT-4o), even for single-turn, non-chat requests.
            # This is the recommended approach by OpenAI for accessing their latest models.
            #thats why I use this endpoint
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
            print(f"Error handling OpenAI request: {e}")
            return f"An error occurred: {e}"


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
    
    