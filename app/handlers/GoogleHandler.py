import google.generativeai as genai
from typing import Union, AsyncIterable, Dict, Any, Optional
from app.DB_connection.chat_manager import chat_history
from app.handlers.BaseHandler import BaseHandler
import os
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_logger import log_response

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

    async def sync_handle(self, user_prompt: str,chat_id:UUID | None, request_id: UUID) -> Dict[str, Any]:
        try:
            
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            response = await self.model.generate_content_async(formatted_messages)

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
        
    async def stream_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        
        async def stream_and_finalize():
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            full_response = ""
            try:
                response_stream = await self.model.generate_content_async(formatted_messages, stream=True)
                
                async for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                    yield chunk
                
                # After the stream is complete, log the response
                await log_response(ResponseLog(
                    request_id=request_id,
                    response=full_response,
                    input_tokens=response_stream.usage_metadata.prompt_token_count,
                    output_tokens=response_stream.usage_metadata.candidates_token_count,
                    status=True,  # Assuming success if stream completes
                ))

            except Exception as e:
                print(f"Error handling Google stream: {e}")
                await log_response(ResponseLog(
                    request_id=request_id,
                    response=full_response,
                    error_message=str(e),
                    status=False,
                ))
                yield f"An error occurred: {e}"

        return stream_and_finalize()
        
        
    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available Google models. 
        This is a static method so it can be called without creating an instance.
        """
        return [model.name for model in genai.list_models()]
    
    @staticmethod
    async def chat_complier(userprompt:str,chat_id:UUID | None) -> list[Dict[str, str]]:
        """
        This method is used to compile the user prompt into a list of messages for the model.
        """
        history = await chat_history(chat_id)
        formatted_messages = []
        for message in history:
            formatted_messages.append({"role": "user", "parts": [message["request"]]})
            formatted_messages.append({"role": "model", "parts": [message["response"]]})
        
        # Add the latest user prompt
        formatted_messages.append({"role": "user", "parts": [userprompt]})
        
        return formatted_messages
