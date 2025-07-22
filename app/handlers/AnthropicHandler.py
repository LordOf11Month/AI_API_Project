from typing import Union, AsyncIterable, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.handlers.BaseHandler import BaseHandler


class AnthropicHandler(BaseHandler):
    """
    Handler for Anthropic's Claude models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncAnthropic()

    async def handle(self, prompt: str, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """
        Processes a prompt and returns the model's response.
        """
        messages = [{"role": "user", "content": prompt}]
        
        try:
            if stream:
                async def stream_generator():
                    async with self.client.messages.stream(
                        model=self.model_name,
                        messages=messages,
                        system=self.system_instruction,
                        **self.generation_config
                    ) as stream:
                        async for text in stream.text_stream:
                            yield text
                return stream_generator()
            else:
                response = await self.client.messages.create(
                    model=self.model_name,
                    messages=messages,
                    system=self.system_instruction,
                    **self.generation_config
                )
                return response.content[0].text
        except Exception as e:
            print(f"Error handling Anthropic request: {e}")
            return f"An error occurred: {e}"

    @staticmethod
    def get_models(self) -> list[str]:
        """`
        Get a list of available Anthropic models.
        """


        # this place need testing!!!!!!!---------------------

        models = self.client.models.list(limit=20)
        return [model.name for model in models]
        