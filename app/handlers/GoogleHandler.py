import google.generativeai as genai
from typing import Union, AsyncIterable, Dict, Any, Optional
from app.DB_connection.chat_manager import chat_history
from app.handlers.BaseHandler import BaseHandler
import os
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import finalize_request
from app.utils.debug_logger import debug_log


class GoogleHandler(BaseHandler):
    """
    Handler for Google's Generative AI models.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            genai.configure(api_key=google_api_key)
        else:
            debug_log("Warning: GOOGLE_API_KEY environment variable not set.", "[GoogleHandler]")
        super().__init__(model_name, generation_config, system_instruction)
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=self.system_instruction
        )

    async def sync_handle(self, user_prompt: str,chat_id:UUID | None, request_id: UUID) -> Dict[str, Any]:
        try:
            debug_log(f"Starting sync_handle for request_id: {request_id}", "[GoogleHandler]")
            debug_log(f"Compiling messages with prompt: {user_prompt}", "[GoogleHandler]")
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            debug_log(f"Formatted messages: {formatted_messages}", "[GoogleHandler]")
            
            try:
                debug_log("Calling Google API...", "[GoogleHandler]")
                response = await self.model.generate_content_async(formatted_messages)
                debug_log("Received response from Google API", "[GoogleHandler]")
            except asyncio.CancelledError:
                debug_log("Request was cancelled during API call", "[GoogleHandler]")
                # Start logging but don't await it
                asyncio.create_task(finalize_request(ResponseLog(
                    request_id=request_id,
                    response="Request cancelled",
                    input_tokens=0,
                    output_tokens=0,
                    status=False,
                    error_message="Request was cancelled during processing"
                )))
                raise  # Re-raise the cancellation

            # Extract the response text
            response_text = response.candidates[0].content.parts[0].text
            debug_log(f"Extracted response text: {response_text[:100]}...", "[GoogleHandler]")

            # Start logging but don't await it
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                response=response_text,
                status=response.candidates[0].finish_reason.name == "STOP",
            )))

            debug_log("Successfully completed request", "[GoogleHandler]")
            # Return response immediately while logging continues in background
            return {"response": response_text}

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):  # Don't log cancelled errors twice
                debug_log(f"Error occurred: {str(e)}", "[GoogleHandler]")
                debug_log(f"Error type: {type(e)}", "[GoogleHandler]")
                # Start error logging but don't await it
                asyncio.create_task(finalize_request(ResponseLog(
                    request_id=request_id,
                    response="",
                    input_tokens=0,
                    output_tokens=0,
                    status=False,
                    error_message=str(e)
                )))
            raise  # Re-raise the exception to be handled by FastAPI
        
    async def stream_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        debug_log(f"Starting stream_handle for request_id: {request_id}", "[GoogleHandler]")
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        debug_log(f"Formatted messages for stream: {formatted_messages}", "[GoogleHandler]")

        full_response = ""
        try:
            debug_log("Starting streaming request to Google API", "[GoogleHandler]")
            response_stream = await self.model.generate_content_async(formatted_messages, stream=True)
            
            debug_log("Processing stream chunks", "[GoogleHandler]")
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    debug_log(f"Received chunk: {content[:50]}...", "[GoogleHandler]")
                yield {"response": content}
            
            # After the stream is complete, log the response
            debug_log("Stream completed, logging to database", "[GoogleHandler]")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=response_stream.usage_metadata.prompt_token_count,
                output_tokens=response_stream.usage_metadata.candidates_token_count,
                status=True,  # Assuming success if stream completes
            )))

        except asyncio.CancelledError:
            debug_log("Stream was cancelled", "[GoogleHandler]")
            # Handle cancellation by logging it and cleaning up
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=0,
                output_tokens=0,
                status=False,
                error_message="Stream was cancelled during processing"
            )))
            raise  # Re-raise the cancellation

        except Exception as e:
            debug_log(f"Stream error occurred: {str(e)}", "[GoogleHandler]")
            debug_log(f"Stream error type: {type(e)}", "[GoogleHandler]")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                error_message=str(e),
                status=False,
                input_tokens=0,
                output_tokens=0
            )))
            yield {"error": str(e)}

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
