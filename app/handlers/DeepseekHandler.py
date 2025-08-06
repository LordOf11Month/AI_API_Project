import traceback
from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
import time
from uuid import UUID
from app.models.DataModels import RequestFinal, Response, message, Tool
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
        debug(f"Compiling messages", "[DeepSeekHandler]")
        formatted_messages = []
        
        # Add system instruction if available
        if self.system_instruction:
            formatted_messages.append({"role": "system", "content": self.system_instruction})
        
        # Add all messages
        for msg in messages:
            formatted_messages.append({"role": msg.role.value, "content": msg.content})
        
        debug(f"Chat compiled. Total messages: {len(formatted_messages)}", "[DeepSeekHandler]")
        return formatted_messages

    async def response_parser(self, response: Dict[str, Any]) -> Response:
        """
        Parses the response from the DeepSeek API.
        """
        if response.output[0].message.content:
            return Response(type="message", content=response.output[0].message.content)
        elif response.output[0].message.tool_calls:
            return Response(type="function_call", function_name=response.output[0].message.tool_calls[0].function.name, function_args=response.output[0].message.tool_calls[0].function.arguments)
        else:
            return Response(type="error", error="No content returned.")
    
    async def sync_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> Dict[str, Any]:
        """
        Handles a non-streaming (synchronous) request.
        """
        info(f"Handling synchronous request for model: {self.model_name}", "[DeepSeekHandler]")
        formatted_messages = await self.message_complier(messages)
        
        # Get timeout from environment variable (default: 30 seconds)
        timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
        debug(f"Using API timeout: {timeout_seconds} seconds", "[DeepSeekHandler]")
        
        try:
            debug("Sending request to DeepSeek API.", "[DeepSeekHandler]")
            latency = time.time()
            
            # Add timeout to the API call
            response = await asyncio.wait_for(
                self.client.responses.create(
                    model=self.model_name,
                    input=formatted_messages,
                    **self.generation_config,
                    tools=tools,
                    tool_choice="auto" if tools else None
                ),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            debug("Received synchronous response from API.", "[DeepSeekHandler]")

            result = response.output[0]  # Get the first output message

            debug(f"finalizing request for request_id: {request_id}", "[DeepSeekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=response.usage.input_tokens if response.usage else None,
                output_tokens=response.usage.output_tokens if response.usage else None,
                reasoning_tokens=response.usage.output_tokens_details.reasoning_tokens if response.usage and response.usage.output_tokens_details else None,
                latency=latency,
                status=response.status == "completed"
            ))
            info("Synchronous request finalized successfully.", "[DeepSeekHandler]")

            return result

        except asyncio.TimeoutError:
            error(f"DeepSeek API request timed out after {timeout_seconds} seconds", "[DeepSeekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            raise ValueError(f"API request timed out after {timeout_seconds} seconds")
        except Exception as e:
            error(f"An error occurred during sync handle: {e}\nStack trace: {traceback.format_exc()}", "[DeepSeekHandler]")
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
        
    async def stream_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[DeepSeekHandler]")
        formatted_messages = await self.message_complier(messages)

        # Get timeout from environment variable (default: 60 seconds for streaming)
        timeout_seconds = int(os.getenv("API_STREAM_TIMEOUT_SECONDS", "60"))
        debug(f"Using streaming API timeout: {timeout_seconds} seconds", "[DeepSeekHandler]")

        full_response = ""
        latency = time.time()
        tool_calls_buffer = []
        try:
            debug("Sending streaming request to DeepSeek API.", "[DeepSeekHandler]")
            
            # Add timeout to the streaming API call
            response_stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config,
                    stream=True,
                    tools=tools,
                    tool_choice="auto" if tools else None
                ),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            
            debug("Processing stream chunks...", "[DeepSeekHandler]")
            async for chunk in response_stream:
                delta = chunk.choices[0].delta
                
                # Handle regular content
                if delta.content:
                    content = delta.content
                    full_response += content
                    debug(f"Received stream chunk: {content[:50]}...", "[DeepSeekHandler]")
                    yield f"data: {content}\n\n"
                
                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        # Ensure we have enough space in the buffer
                        while len(tool_calls_buffer) <= tool_call.index:
                            tool_calls_buffer.append({
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        
                        # Update the tool call at the correct index
                        if tool_call.id:
                            tool_calls_buffer[tool_call.index]["id"] = tool_call.id
                        if tool_call.function.name:
                            tool_calls_buffer[tool_call.index]["function"]["name"] = tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls_buffer[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
                    
                    # Yield tool call data in a structured format
                    yield f"data: {{'tool_calls': {tool_calls_buffer}}}\n\n"
            
            info("Streaming finished.", "[DeepSeekHandler]")

        except asyncio.TimeoutError:
            error(f"DeepSeek streaming API request timed out after {timeout_seconds} seconds", "[DeepSeekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            yield f"data: Request timed out after {timeout_seconds} seconds\n\n"
        except Exception as e:
            error(f"An error occurred during stream handle: {e}\nStack trace: {traceback.format_exc()}", "[DeepSeekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[DeepSeekHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,  # Token counts not available in streaming for DeepSeek
                output_tokens=None,
                reasoning_tokens=None,
                latency=latency,
                status=True
            ))
            info("Full streaming request finalized successfully.", "[DeepSeekHandler]")
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
    
    