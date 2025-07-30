from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import finalize_request
from app.DB_connection.chat_manager import chat_history


class OpenAIHandler(BaseHandler):
    """
    Handler for OpenAI's GPT models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncOpenAI()

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        try:
            print(f"[OpenAIHandler] Starting sync_handle for request_id: {request_id}")
            print(f"[OpenAIHandler] Compiling messages with prompt: {user_prompt}")
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            if self.system_instruction:
                formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})
            print(f"[OpenAIHandler] Formatted messages: {formatted_messages}")

            try:
                print("[OpenAIHandler] Calling OpenAI API...")
                # Note: The 'chat.completions' endpoint is the current standard for all modern
                # OpenAI models (e.g., GPT-4, GPT-4o), even for single-turn, non-chat requests.
                # This is the recommended approach by OpenAI for accessing their latest models.
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config
                )
                print("[OpenAIHandler] Received response from OpenAI API")
            except asyncio.CancelledError:
                print("[OpenAIHandler] Request was cancelled during API call")
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

            # Extract the response content
            response_content = response.choices[0].message.content
            print(f"[OpenAIHandler] Extracted response content: {response_content[:100]}...")

            # Start logging but don't await it
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                response=response_content,
                status=response.choices[0].finish_reason == "stop",
            )))

            print("[OpenAIHandler] Successfully completed request")
            # Return response immediately while logging continues in background
            return {"response": response_content}

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):  # Don't log cancelled errors twice
                print(f"[OpenAIHandler] Error occurred: {str(e)}")
                print(f"[OpenAIHandler] Error type: {type(e)}")
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
        print(f"[OpenAIHandler] Starting stream_handle for request_id: {request_id}")
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        if self.system_instruction:
            formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})
        print(f"[OpenAIHandler] Formatted messages for stream: {formatted_messages}")

        full_response = ""
        try:
            print("[OpenAIHandler] Starting streaming request to OpenAI API")
            response_stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                **self.generation_config,
                stream=True
            )
            
            print("[OpenAIHandler] Processing stream chunks")
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    print(f"[OpenAIHandler] Received chunk: {content[:50]}...")
                yield {"response": content}
            
            # After the stream is complete, log the response
            print("[OpenAIHandler] Stream completed, logging to database")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=0, # Not available for streaming
                output_tokens=0, # Not available for streaming
                status=True,  # Assuming success if stream completes
            )))

        except asyncio.CancelledError:
            print("[OpenAIHandler] Stream was cancelled")
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
            print(f"[OpenAIHandler] Stream error occurred: {str(e)}")
            print(f"[OpenAIHandler] Stream error type: {type(e)}")
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
        Return all available OpenAI models. 
        This is a static method so it can be called without creating an instance.
        """
        try:
            client = OpenAI()
            return [model.id for model in client.models.list()]
        except Exception as e:
            print(f"Error getting OpenAI models: {e}")
            return []
    
    @staticmethod
    async def chat_complier(userprompt:str,chat_id:UUID | None) -> list[Dict[str, str]]:
        """
        This method is used to compile the user prompt into a list of messages for the model.
        """
        history = await chat_history(chat_id)
        formatted_messages = []
        for message in history:
            formatted_messages.append({"role": "user", "content": message["request"]})
            formatted_messages.append({"role": "assistant", "content": message["response"]})
        
        # Add the latest user prompt
        formatted_messages.append({"role": "user", "content": userprompt})
        
        return formatted_messages
    
    