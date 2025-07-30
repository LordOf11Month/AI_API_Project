from typing import Union, AsyncIterable, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import finalize_request
from app.DB_connection.chat_manager import chat_history


class AnthropicHandler(BaseHandler):
    """
    Handler for Anthropic's Claude models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncAnthropic()

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        try:
            print(f"[AnthropicHandler] Starting sync_handle for request_id: {request_id}")
            print(f"[AnthropicHandler] Compiling messages with prompt: {user_prompt}")
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            print(f"[AnthropicHandler] Formatted messages: {formatted_messages}")
            
            try:
                print("[AnthropicHandler] Calling Anthropic API...")
                response = await self.client.messages.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    system=self.system_instruction,
                    **self.generation_config
                )
                print("[AnthropicHandler] Received response from Anthropic API")
            except asyncio.CancelledError:
                print("[AnthropicHandler] Request was cancelled during API call")
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
            response_content = response.content[0].text
            print(f"[AnthropicHandler] Extracted response content: {response_content[:100]}...")

            # Start logging but don't await it
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                response=response_content,
                status=response.stop_reason == "end_turn",
            )))

            print("[AnthropicHandler] Successfully completed request")
            # Return response immediately while logging continues in background
            return {"response": response_content}

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):  # Don't log cancelled errors twice
                print(f"[AnthropicHandler] Error occurred: {str(e)}")
                print(f"[AnthropicHandler] Error type: {type(e)}")
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
        print(f"[AnthropicHandler] Starting stream_handle for request_id: {request_id}")
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        print(f"[AnthropicHandler] Formatted messages for stream: {formatted_messages}")
        
        full_response = ""
        try:
            print("[AnthropicHandler] Starting streaming request to Anthropic API")
            async with self.client.messages.stream(
                model=self.model_name,
                messages=formatted_messages,
                system=self.system_instruction,
                **self.generation_config
            ) as response_stream:
                print("[AnthropicHandler] Processing stream chunks")
                async for chunk in response_stream.text_stream:
                    full_response += chunk
                    print(f"[AnthropicHandler] Received chunk: {chunk[:50]}...")
                    yield {"response": chunk}
                
                final_message = await response_stream.get_final_message()
            
            # After the stream is complete, log the response
            print("[AnthropicHandler] Stream completed, logging to database")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=final_message.usage.input_tokens,
                output_tokens=final_message.usage.output_tokens,
                status=True,  # Assuming success if stream completes
            )))

        except asyncio.CancelledError:
            print("[AnthropicHandler] Stream was cancelled")
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
            print(f"[AnthropicHandler] Stream error occurred: {str(e)}")
            print(f"[AnthropicHandler] Stream error type: {type(e)}")
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
        """`
        Get a list of available Anthropic models.
        """
        try:
            # Note: Anthropic SDK doesn't have a direct equivalent of OpenAI's `models.list()`.
            # Officially, they recommend referring to their documentation for model names.
            # For this reason, we'll return a static list of commonly used models.
            # You can update this list as new models are released.
            return [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
        except Exception as e:
            print(f"Error getting Anthropic models: {e}")
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
        