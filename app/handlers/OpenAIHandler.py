from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
import time
import os
import traceback
import json
from uuid import UUID
from app.models.DataModels import RequestFinal, Response, Tool, message
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

    async def response_parser(self, response: Dict[str, Any]) -> Response:
        """
        Parses the response from the OpenAI API.
        """
        # Check the type of the output directly
        if hasattr(response.output[0], 'type') and response.output[0].type == 'function_call':
            return Response(type="function_call", function_name=response.output[0].name, function_args=json.loads(response.output[0].arguments))
        elif hasattr(response.output[0], 'content') and response.output[0].content:
            # Handle the new response format where content is a list of ResponseOutputText objects
            if isinstance(response.output[0].content, list) and len(response.output[0].content) > 0:
                # Extract text from the first content item
                content_text = response.output[0].content[0].text
                return Response(type="message", content=content_text)
            else:
                # Fallback for older format or empty content
                return Response(type="message", content=str(response.output[0].content))
        else:
            return Response(type="error", error="No content returned.")
    
    async def sync_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> Dict[str, Any]:
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
            debug("Received synchronous response from API.", "[OpenAIHandler]")


            debug(f"finalizing request for request_id: {request_id}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=response.usage.input_tokens if response.usage else None,
                output_tokens=response.usage.output_tokens if response.usage else None,
                reasoning_tokens=response.usage.output_tokens_details.reasoning_tokens if response.usage and response.usage.output_tokens_details else None,
                latency=latency,
                status=response.status == "completed"
            ))
            info("Synchronous request finalized successfully.", "[OpenAIHandler]")
            debug(f"response.output[0]: {response.output[0]}", "[OpenAIHandler]")
            
            # Check the type of the output directly
            if hasattr(response.output[0], 'type') and response.output[0].type == 'function_call':
                return Response(type="function_call", function_name=response.output[0].name, function_args=json.loads(response.output[0].arguments))
            elif hasattr(response.output[0], 'content') and response.output[0].content:
                # Handle the new response format where content is a list of ResponseOutputText objects
                if isinstance(response.output[0].content, list) and len(response.output[0].content) > 0:
                    # Extract text from the first content item
                    content_text = response.output[0].content[0].text
                    return Response(type="message", content=content_text)
                else:
                    # Fallback for older format or empty content
                    return Response(type="message", content=str(response.output[0].content))
            else:
                return Response(type="error", error="No content returned.")

        except asyncio.TimeoutError:
            error(f"OpenAI API request timed out after {timeout_seconds} seconds", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            return Response(type="error", error=f"API request timed out after {timeout_seconds} seconds")
        except Exception as e:
            error(f"An error occurred during sync handle at line {e.__traceback__.tb_lineno}: {e} \nStack trace: {traceback.format_exc()}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,
                output_tokens=None,
                reasoning_tokens=None,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            return Response(type="error", error=str(e))
        
    async def stream_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> AsyncIterable[Dict[str, Any]]:
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
        tool_calls_buffer = []
        try:
            debug("Sending streaming request to OpenAI API.", "[OpenAIHandler]")
            
            # Add timeout to the streaming API call
            response_stream = await asyncio.wait_for(
                self.client.responses.create(
                    model=self.model_name,
                    input=formatted_messages,
                    **self.generation_config,
                    stream=True,
                    tools=tools,
                    tool_choice="auto" if tools else None
                ),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            
            debug("Processing stream chunks...", "[OpenAIHandler]")
            debug(f"Response stream object type: {type(response_stream)}", "[OpenAIHandler]")
            
            # Keep track of function calls being built
            current_function_calls = {}
            
            async for chunk in response_stream:
                debug(f"Received chunk type: {chunk.type}, content: {chunk}", "[OpenAIHandler]")
                
                # Handle function call argument streaming
                if chunk.type == "response.function_call_arguments.delta":
                    if chunk.item_id not in current_function_calls:
                        current_function_calls[chunk.item_id] = {"arguments": ""}
                    current_function_calls[chunk.item_id]["arguments"] += chunk.delta
                
                # Handle function call completion
                elif chunk.type == "response.function_call_arguments.done":
                    if chunk.item_id in current_function_calls:
                        tool_call = {
                            "id": chunk.item_id,
                            "type": "function",
                            "function": {
                                "name": "get_weather",  # This should be retrieved from the initial tool call event
                                "arguments": chunk.arguments
                            }
                        }
                        yield f"data: {{'tool_calls': [{tool_call}]}}\n\n"
                
                # Handle regular content streaming
                elif chunk.type == "response.output_text.delta":
                    content = chunk.delta
                    debug(f"Received content chunk: {content[:50]}...", "[OpenAIHandler]")
                    yield f"data: {content}\n\n"
                
                # Handle initial function call setup
                elif chunk.type == "response.output_item.added":
                    if hasattr(chunk.item, 'type') and chunk.item.type == 'function_call':
                        current_function_calls[chunk.item.id] = {
                            "name": chunk.item.name,
                            "arguments": ""
                        }
            
            info("Streaming finished.", "[OpenAIHandler]")

        except asyncio.TimeoutError:
            error(f"OpenAI streaming API request timed out after {timeout_seconds} seconds", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            yield f"data: An error occurred: {f'Request timed out after {timeout_seconds} seconds'}\n\n"

        except Exception as e:
            error(f"An error occurred during stream handle at line {e.__traceback__.tb_lineno}: {e} \nStack trace: {traceback.format_exc()}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[OpenAIHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=None,  # Token counts not available in streaming for OpenAI
                output_tokens=None,
                reasoning_tokens=None,
                latency=latency,
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
            error(f"Failed to fetch models from OpenAI, will send default list. error: {e}", "[OpenAIHandler]")
            return ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo']
    
    