from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
import time
import os
from uuid import UUID
from app.models.DataModels import RequestFinal, message
from app.DB_connection.request_manager import finalize_request
from app.utils.console_logger import info, warning, error, debug


class OpenAIHandler(BaseHandler):
    """
    Handler for OpenAI's GPT models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str], API_KEY: str):
        super().__init__(model_name, generation_config, system_instruction, API_KEY)
        self.client = AsyncOpenAI(api_key=self.API_KEY)
        debug(f"OpenAI client initialized for model '{self.model_name}'.", "[OpenAIHandler]")

    async def message_complier(self, messages: list[message]) -> list[Dict[str, str]]:
        """
        Compiles the list of messages formatted for the AI model.
        """
        debug(f"Compiling messages", "[OpenAIHandler]")
        formatted_messages = []
        
        # Add system instruction if available
        if self.system_instruction:
            formatted_messages.append({"role": "system", "content": self.system_instruction})
        
        # Add all messages
        for msg in messages:
            formatted_messages.append({"role": msg.role.value, "content": msg.content})
        
        debug(f"Chat compiled. Total messages: {len(formatted_messages)}", "[OpenAIHandler]")
        return formatted_messages

    async def sync_handle(self, messages: list[message], request_id: UUID) -> Dict[str, Any]:
        """
        Handles a non-streaming (synchronous) request.
        """
        info(f"Handling synchronous request for model: {self.model_name}", "[OpenAIHandler]")
        formatted_messages = await self.message_complier(messages)
        
        # Get timeout from environment variable (default: 30 seconds)
        timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
        debug(f"Using API timeout: {timeout_seconds} seconds", "[OpenAIHandler]")
        
        try:
            debug("Sending request to OpenAI API.", "[OpenAIHandler]")
            latency = time.time()
            
            # Add timeout to the API call
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config
                ),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            debug("Received synchronous response from API.", "[OpenAIHandler]")

            response_content = response.choices[0].message.content
            debug(f"Extracted response content: {response_content[:100]}...", "[OpenAIHandler]")

            debug(f"finalizing request for request_id: {request_id}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                reasoning_tokens=None,  # OpenAI doesn't provide reasoning tokens
                latency=latency,
                status=response.choices[0].finish_reason == "stop"
            ))
            info("Synchronous request finalized successfully.", "[OpenAIHandler]")

            return response_content

        except asyncio.TimeoutError:
            error(f"OpenAI API request timed out after {timeout_seconds} seconds", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            raise ValueError(f"API request timed out after {timeout_seconds} seconds")
        except Exception as e:
            error(f"An error occurred during sync handle: {e}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,
                output_tokens=None,
                reasoning_tokens=None,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            raise
        
    async def stream_handle(self, messages: list[message], request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[OpenAIHandler]")
        formatted_messages = await self.message_complier(messages)

        # Get timeout from environment variable (default: 60 seconds for streaming)
        timeout_seconds = int(os.getenv("API_STREAM_TIMEOUT_SECONDS", "60"))
        debug(f"Using streaming API timeout: {timeout_seconds} seconds", "[OpenAIHandler]")

        full_response = ""
        latency = time.time()
        try:
            debug("Sending streaming request to OpenAI API.", "[OpenAIHandler]")
            
            # Add timeout to the streaming API call
            response_stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config,
                    stream=True
                ),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            
            debug("Processing stream chunks...", "[OpenAIHandler]")
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    debug(f"Received stream chunk: {content[:50]}...", "[OpenAIHandler]")
                    yield f"data: {content}\n\n"
            
            info("Streaming finished.", "[OpenAIHandler]")

        except asyncio.TimeoutError:
            error(f"OpenAI streaming API request timed out after {timeout_seconds} seconds", "[OpenAIHandler]")
            yield f"data: Request timed out after {timeout_seconds} seconds\n\n"
        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[OpenAIHandler]")
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,  # Token counts not available in streaming for OpenAI
                output_tokens=None,
                reasoning_tokens=None,
                latency=None,
                status=True
            ))
            info("Full streaming request finalized successfully.", "[OpenAIHandler]")
            yield "data: [DONE]\n\n"

    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available OpenAI models. 
        This is a static method so it can be called without creating an instance.
        """
        debug("Fetching available models for OpenAI.", "[OpenAIHandler]")
        try:
            client = OpenAI()
            models = [model.id for model in client.models.list()]
            debug(f"Found models: {models}", "[OpenAIHandler]")
            return models
        except Exception as e:
            error(f"Failed to fetch models from OpenAI: {e}", "[OpenAIHandler]")
            return []
    
    