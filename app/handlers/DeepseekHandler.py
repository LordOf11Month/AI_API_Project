import os
from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import finalize_request
from app.DB_connection.chat_manager import chat_history


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

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        try:
            print(f"[DeepseekHandler] Starting sync_handle for request_id: {request_id}")
            print(f"[DeepseekHandler] Compiling messages with prompt: {user_prompt}")
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            if self.system_instruction:
                formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})
            print(f"[DeepseekHandler] Formatted messages: {formatted_messages}")

            try:
                print("[DeepseekHandler] Calling Deepseek API...")
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config
                )
                print("[DeepseekHandler] Received response from Deepseek API")
            except asyncio.CancelledError:
                print("[DeepseekHandler] Request was cancelled during API call")
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
            print(f"[DeepseekHandler] Extracted response content: {response_content[:100]}...")

            # Start logging but don't await it
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                response=response_content,
                status=response.choices[0].finish_reason == "stop",
            )))

            print("[DeepseekHandler] Successfully completed request")
            # Return response immediately while logging continues in background
            return {"response": response_content}

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):  # Don't log cancelled errors twice
                print(f"[DeepseekHandler] Error occurred: {str(e)}")
                print(f"[DeepseekHandler] Error type: {type(e)}")
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
        print(f"[DeepseekHandler] Starting stream_handle for request_id: {request_id}")
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        if self.system_instruction:
            formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})
        print(f"[DeepseekHandler] Formatted messages for stream: {formatted_messages}")

        full_response = ""
        try:
            print("[DeepseekHandler] Starting streaming request to Deepseek API")
            response_stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                **self.generation_config,
                stream=True
            )
            
            print("[DeepseekHandler] Processing stream chunks")
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    print(f"[DeepseekHandler] Received chunk: {content[:50]}...")
                yield {"response": content}
            
            # After the stream is complete, log the response
            print("[DeepseekHandler] Stream completed, logging to database")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=0, # Not available for streaming
                output_tokens=0, # Not available for streaming
                status=True,  # Assuming success if stream completes
            )))

        except asyncio.CancelledError:
            print("[DeepseekHandler] Stream was cancelled")
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
            print(f"[DeepseekHandler] Stream error occurred: {str(e)}")
            print(f"[DeepseekHandler] Stream error type: {type(e)}")
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