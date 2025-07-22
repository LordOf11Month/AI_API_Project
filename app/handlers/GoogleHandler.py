import google.generativeai as genai
from typing import Union, AsyncIterable, Dict, Any, Optional
from app.handlers.BaseHandler import BaseHandler

# NOTE: It's recommended to call genai.configure(api_key="YOUR_API_KEY") 
# once on application startup (e.g., in your main server.py).


class GoogleHandler(BaseHandler):
    """
    Handler for Google's Generative AI models.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=self.system_instruction
        )

    async def handle(self, prompt: str, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        try:
            response = await self.model.generate_content_async(prompt, stream=stream)
            if stream:
                async def stream_generator():
                    async for chunk in response:
                        # In some cases, parts can be empty, so filter them out.
                        if chunk.parts:
                            yield chunk.text
                return stream_generator()
            else:
                return response.text
        except Exception as e:
            # Basic error handling. You may want to add more robust logging.
            print(f"Error handling Google request: {e}")
            # You might want to raise a specific HTTP exception here.
            return f"An error occurred: {e}"
        
    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available Google models. 
        This is a static method so it can be called without creating an instance.
        """
        return [model.name for model in genai.list_models()]