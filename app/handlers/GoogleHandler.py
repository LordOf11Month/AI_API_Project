import google.generativeai as genai
from typing import Union, AsyncIterable, Dict, Any, Optional
from app.handlers.BaseHandler import BaseHandler
import os
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.logging.request_logger import log_response

# NOTE: It's recommended to call genai.configure(api_key="YOUR_API_KEY") 
# once on application startup (e.g., in your main server.py).


class GoogleHandler(BaseHandler):
    """
    Handler for Google's Generative AI models.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            genai.configure(api_key=google_api_key)
        else:
            print("Warning: GOOGLE_API_KEY environment variable not set.")
        super().__init__(model_name, generation_config, system_instruction)
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=self.system_instruction
        )

    async def sync_handle(self, messages: list[Dict[str, str]], request_id: UUID) -> Dict[str, Any]:
        try:
            response = await self.model.generate_content_async(messages)

            asyncio.create_task(log_response(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                response=response.candidates[0].content.parts[0].text,
                status=response.candidates[0].finish_reason.name == "STOP",
            )))
            return response
        except Exception as e:
            print(f"Error handling Google request: {e}")
            return f"An error occurred: {e}"
        
    async def stream_handle(self, messages: list[Dict[str, str]]) -> AsyncIterable[Dict[str, Any]]:
        try:
            response = self.model.generate_content_async(messages, stream=True)
            async for chunk in response:
                yield chunk
        except Exception as e:
            print(f"Error handling Google request: {e}")
            yield f"An error occurred: {e}"
        
        
    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available Google models. 
        This is a static method so it can be called without creating an instance.
        """
        return [model.name for model in genai.list_models()]