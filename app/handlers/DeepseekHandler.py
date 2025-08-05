from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
import time
from uuid import UUID
from app.models.DataModels import RequestFinal, message, Tool
from app.DB_connection.request_manager import finalize_request
from app.utils.console_logger import info, warning, error, debug
import os

class DeepseekHandler(BaseHandler):
    """
    Handler for Deepseek's models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str], API_KEY: str):
        super().__init__(model_name, generation_config, system_instruction, API_KEY)
        self.client = AsyncOpenAI(
            api_key=self.API_KEY,
            base_url="https://api.deepseek.com/v1"
        )
        debug(f"Deepseek client initialized for model '{self.model_name}'.", "[DeepseekHandler]")

    async def message_complier(self, messages: list[message]) -> list[Dict[str, str]]:
        """
        Compiles the list of messages formatted for the AI model.
        """
        debug(f"Compiling messages", "[DeepseekHandler]")
        formatted_messages = []
        
        # Add system instruction if available
        if self.system_instruction:
            formatted_messages.append({"role": "system", "content": self.system_instruction})
        
        # Add all messages
        for msg in messages:
            formatted_messages.append({"role": msg.role.value, "content": msg.content})
        
        debug(f"Chat compiled. Total messages: {len(formatted_messages)}", "[DeepseekHandler]")
        return formatted_messages

    def _standardize_message_response(self, response) -> Dict[str, Any]:
        """
        Convert Deepseek response to standardized OpenAI-like message format.
        """
        message_obj = response.choices[0].message
        
        # Create standardized message object
        standardized = {
            "id": f"msg_{response.id}",
            "role": message_obj.role,
            "content": []
        }
        
        # Add text content
        if message_obj.content:
            standardized["content"].append({
                "type": "text", 
                "text": message_obj.content
            })
        
        # Add tool calls if present
        if hasattr(message_obj, 'tool_calls') and message_obj.tool_calls:
            standardized["tool_calls"] = message_obj.tool_calls
            
        return standardized

    async def sync_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> Dict[str, Any]:
        """
        Handles a non-streaming (synchronous) request.
        """
        info(f"Handling synchronous request for model: {self.model_name}", "[DeepseekHandler]")
        formatted_messages = await self.message_complier(messages)
        
        # Get timeout from environment variable (default: 30 seconds)
        timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
        debug(f"Using API timeout: {timeout_seconds} seconds", "[DeepseekHandler]")
        
        try:
            debug("Sending request to Deepseek API.", "[DeepseekHandler]")
            latency = time.time()
            
            # Add timeout to the API call
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    tools=[tool.model_dump() for tool in tools] if tools else None,
                    tool_choice="auto" if tools else None,
                    **self.generation_config
                ),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            debug("Received synchronous response from API.", "[DeepseekHandler]")

            # Standardize the response to match OpenAI format
            result = self._standardize_message_response(response)
            debug(f"Extracted response content: {result['content'][0]['text'][:100] if result['content'] else 'No content'}...", "[DeepseekHandler]")

            debug(f"finalizing request for request_id: {request_id}", "[DeepseekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                reasoning_tokens=response.usage.reasoning_tokens if response.usage and hasattr(response.usage, 'reasoning_tokens') else None,
                latency=latency,
                status=response.choices[0].finish_reason == "stop"
            ))
            info("Synchronous request finalized successfully.", "[DeepseekHandler]")

            return result

        except asyncio.TimeoutError:
            error(f"Deepseek API request timed out after {timeout_seconds} seconds", "[DeepseekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=timeout_seconds,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            raise ValueError(f"API request timed out after {timeout_seconds} seconds")
        except Exception as e:
            error(f"An error occurred during sync handle: {e}", "[DeepseekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,
                output_tokens=None,
                reasoning_tokens=None,
                latency=latency if 'latency' in locals() else None,
                status=False,
                error_message=str(e)
            ))
            raise
        
    async def stream_handle(self, messages: list[message], request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[DeepseekHandler]")
        formatted_messages = await self.message_complier(messages)

        # Get timeout from environment variable (default: 60 seconds for streaming)
        timeout_seconds = int(os.getenv("API_STREAM_TIMEOUT_SECONDS", "60"))
        debug(f"Using streaming API timeout: {timeout_seconds} seconds", "[DeepseekHandler]")

        full_response = ""
        latency = time.time()
        try:
            debug("Sending streaming request to Deepseek API.", "[DeepseekHandler]")
            
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
            
            debug("Processing stream chunks...", "[DeepseekHandler]")
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    debug(f"Received stream chunk: {content[:50]}...", "[DeepseekHandler]")
                    yield f"data: {content}\n\n"
            
            info("Streaming finished.", "[DeepseekHandler]")

        except asyncio.TimeoutError:
            error(f"Deepseek streaming API request timed out after {timeout_seconds} seconds", "[DeepseekHandler]")
            yield f"data: Request timed out after {timeout_seconds} seconds\n\n"
        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[DeepseekHandler]")
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[DeepseekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,  # Token counts not available in streaming for Deepseek
                output_tokens=None,
                reasoning_tokens=None,
                latency=latency if 'latency' in locals() else None,
                status=True
            ))
            info("Full streaming request finalized successfully.", "[DeepseekHandler]")
            yield "data: [DONE]\n\n"

    @staticmethod
    def get_models() -> list[str]:
        """
        Return all available Deepseek models. 
        This is a static method so it can be called without creating an instance.
        """
        debug("Fetching available models for Deepseek.", "[DeepseekHandler]")
        try:
            client = OpenAI(base_url="https://api.deepseek.com/v1",
                            api_key=os.getenv("DEEPSEEK_API_KEY"))
            models = [model.id for model in client.models.list()]
            debug(f"Found models: {models}", "[DeepseekHandler]")
            return models
        except Exception as e:
            error(f"Failed to fetch models from Deepseek: {e}", "[DeepseekHandler]")
            return []
    
    