from typing import Union, AsyncIterable, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.handlers.BaseHandler import BaseHandler
import asyncio
import time
from uuid import UUID
from app.models.DataModels import RequestFinal, Response, message, Tool
from app.DB_connection.request_manager import finalize_request
import os
from app.utils.console_logger import info, warning, error, debug


class AnthropicHandler(BaseHandler):
    """
    Handler for Anthropic's Claude models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str], API_KEY: str):
        super().__init__(model_name, generation_config, system_instruction, API_KEY)
        self.client = AsyncAnthropic(api_key=self.API_KEY)
        debug(f"Anthropic client initialized for model '{self.model_name}'.", "[AnthropicHandler]")

    async def message_complier(self, messages: list[message]) -> list[Dict[str, str]]:
        """
        Compiles the list of messages formatted for the AI model.
        """
        debug(f"Compiling messages", "[AnthropicHandler]")
        formatted_messages = []
        
        # Add all messages (system instruction is handled separately in Anthropic)
        for msg in messages:
            if msg.role.value != "system":  # Anthropic handles system separately
                formatted_messages.append({"role": msg.role.value, "content": msg.content})
        
        debug(f"Chat compiled. Total messages: {len(formatted_messages)}", "[AnthropicHandler]")
        return formatted_messages

    def _convert_tools_to_anthropic_format(self, tools: Optional[list[Tool]]) -> Optional[list[Dict[str, Any]]]:
        """
        Convert our Tool objects to Anthropic-compatible format.
        """
        if not tools:
            return None
        
        anthropic_tools = []
        for tool in tools:
            anthropic_tool = {
                "name": tool.name,
                "description": tool.description or "",
            }
            if tool.parameters:
                anthropic_tool["input_schema"] = tool.parameters
            
            anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools

    def response_parser(self, response) -> Response:
        """
        Convert Anthropic response to standardized Response object.
        """
        if response.content[0].type == "text":
            return Response(type="message", content=response.content[0].text)
        elif response.content[0].type == "tool_use":
            return Response(type="function_call", function_name=response.content[0].name, function_args=response.content[0].input)
        else:
            return Response(type="error", error="No content returned.")

    async def sync_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> Dict[str, Any]:
        """
        Handles a non-streaming (synchronous) request.
        """
        info(f"Handling synchronous request for model: {self.model_name}", "[AnthropicHandler]")
        formatted_messages = await self.message_complier(messages)
        
        # Convert tools to Anthropic format
        anthropic_tools = self._convert_tools_to_anthropic_format(tools)
        
        # Get timeout from environment variable (default: 30 seconds)
        timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
        debug(f"Using API timeout: {timeout_seconds} seconds", "[AnthropicHandler]")
        
        try:
            debug("Sending request to Anthropic API.", "[AnthropicHandler]")
            latency = time.time()
            
            # Prepare request parameters
            request_params = {
                "model": self.model_name,
                "messages": formatted_messages,
                "system": self.system_instruction,
                **self.generation_config
            }
            
            # Add tools if present
            if anthropic_tools:
                request_params["tools"] = anthropic_tools
            
            # Add timeout to the API call
            response = await asyncio.wait_for(
                self.client.messages.create(**request_params),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            debug("Received synchronous response from API.", "[AnthropicHandler]")

            # Standardize the response to match OpenAI format
            result = self.response_parser(response)
            debug(f"Extracted response content: {result['content'][0]['text'][:100] if result['content'] else 'No content'}...", "[AnthropicHandler]")

            debug(f"finalizing request for request_id: {request_id}", "[AnthropicHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=response.usage.input_tokens if response.usage else None,
                output_tokens=response.usage.output_tokens if response.usage else None,
                reasoning_tokens=None,  # Anthropic doesn't provide reasoning tokens
                latency=latency,
                status=response.stop_reason == "end_turn"
            ))
            info("Synchronous request finalized successfully.", "[AnthropicHandler]")

            return result

        except asyncio.TimeoutError:
            error(f"Anthropic API request timed out after {timeout_seconds} seconds", "[AnthropicHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            return Response(type="error", error=f"API request timed out after {timeout_seconds} seconds")
        except Exception as e:
            error(f"An error occurred during sync handle: {e}", "[AnthropicHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,
                output_tokens=None,
                reasoning_tokens=None,
                latency=latency if 'latency' in locals() else None,
                status=False,
                error_message=str(e)
            ))
            return Response(type="error", error=str(e))

    async def stream_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[AnthropicHandler]")
        formatted_messages = await self.message_complier(messages)
            
        # Get timeout from environment variable (default: 60 seconds for streaming)
        timeout_seconds = int(os.getenv("API_STREAM_TIMEOUT_SECONDS", "60"))
        debug(f"Using streaming API timeout: {timeout_seconds} seconds", "[AnthropicHandler]")
        
        latency = time.time()
        final_message = None
        try:
            debug("Sending streaming request to Anthropic API.", "[AnthropicHandler]")
            
            # Add timeout to the streaming API call
            async def stream_with_timeout():
                async with self.client.messages.stream(
                    model=self.model_name,
                    messages=formatted_messages,
                    system=self.system_instruction,
                    **self.generation_config
                ) as response_stream:
                    nonlocal latency, final_message
                    latency = time.time() - latency
                    debug("Processing stream chunks...", "[AnthropicHandler]")
                    async for chunk in response_stream.text_stream:
                        debug(f"Received stream chunk: {chunk[:50]}...", "[AnthropicHandler]")
                        yield f"data: {chunk}\n\n"
                    
                    final_message = await response_stream.get_final_message()
            
            async for chunk in await asyncio.wait_for(stream_with_timeout(), timeout=timeout_seconds):
                yield chunk
            
            info("Streaming finished.", "[AnthropicHandler]")

        except asyncio.TimeoutError:
            error(f"Anthropic streaming API request timed out after {timeout_seconds} seconds", "[AnthropicHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            yield f"data: Request timed out after {timeout_seconds} seconds\n\n"
        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[AnthropicHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[AnthropicHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=final_message.usage.input_tokens if final_message and final_message.usage else None,
                output_tokens=final_message.usage.output_tokens if final_message and final_message.usage else None,
                reasoning_tokens=None,
                latency=latency if 'latency' in locals() else None,
                status=True
            ))
            info("Full streaming request finalized successfully.", "[AnthropicHandler]")
            yield "data: [DONE]\n\n"

    @staticmethod
    def get_models() -> list[str]:
        """
        Get a list of available Anthropic models.
        """
        debug("Fetching available models for Anthropic.", "[AnthropicHandler]")
        try:
            models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022", 
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
            debug(f"Found models: {models}", "[AnthropicHandler]")
            return models
        except Exception as e:
            error(f"Failed to fetch models for Anthropic: {e}", "[AnthropicHandler]")
            return []
        