
import time
import google.generativeai as genai
from typing import Dict, Any, AsyncIterable
from uuid import UUID
import asyncio
import os
from app.handlers.BaseHandler import BaseHandler
from app.DB_connection.request_manager import finalize_request
from app.models.DataModels import RequestFinal, Response, message, Tool  
from typing import Optional
from app.utils.console_logger import info, warning, error, debug
import json

class GoogleHandler(BaseHandler):
    """
    Handles requests for Google's AI models.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: str | None, API_KEY: str):
        super().__init__(model_name, generation_config, system_instruction, API_KEY)
        
        # Configure the generative AI model
        genai.configure(api_key=self.API_KEY)
        
        # Google doesn't accept empty system instructions
        validated_system_instruction = None
        if system_instruction and system_instruction.strip():
            validated_system_instruction = system_instruction
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=validated_system_instruction
        )
        debug(f"Google AI model '{self.model_name}' initialized.", "[GoogleHandler]")

    async def message_complier(self, messages: list[message]) -> list[Dict[str, str]]:
        """
        Compiles the list of messages
        formatted for the AI model.
        """
        debug(f"Compiling messages", "[GoogleHandler]")
        history = []
        for message in messages:
            if not message.content or message.content.strip() == "":
                warning(f"Skipping empty message with role: {message.role.value}", "[GoogleHandler]")
                continue
            history.append({'role': message.role.value, 'parts': [message.content]})
        debug(f"Chat compiled. Total messages: {len(history)}", "[GoogleHandler]")
        return history

    async def response_parser(self, response) -> Response:
        """
        Convert Google AI response to standardized Response object.
        """
        if response.parts:
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    return Response(type="message", content=part.text)
                elif hasattr(part, 'function_call') and part.function_call:
                    return Response(type="function_call", function_name=part.function_call.name, function_args=part.function_call.args)
        else:
            return Response(type="error", error="No content returned.")

    async def sync_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> Dict[str, Any]:
        """
        Handles a non-streaming (synchronous) request.
        """
        info(f"Handling synchronous request for model: {self.model_name}", "[GoogleHandler]")
        Provider_messages = await self.message_complier(messages)
        
        # Get timeout from environment variable (default: 30 seconds)
        timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
        debug(f"Using API timeout: {timeout_seconds} seconds", "[GoogleHandler]")
        
        try:
            debug("Sending request to Google API.", "[GoogleHandler]")
            latency = time.time()
            
            # Prepare request parameters
            request_params = Provider_messages
            
            # Create Google tools if present
            google_tools = None
            if tools:
                google_tools = []
                for tool in tools:
                    # Convert our Tool model to Google's FunctionDeclaration
                    google_tool = genai.types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description or "",
                        parameters=tool.parameters or {}
                    )
                    google_tools.append(google_tool)
            
            # Add timeout to the API call
            response = await asyncio.wait_for(
                self.model.generate_content_async(
                    **request_params, 
                    tools=google_tools if google_tools else None),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
                

            debug(f"finalizing request for request_id: {request_id}", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id, 
                input_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                output_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else None,
                reasoning_tokens=response.usage_metadata.cached_content_token_count if response.usage_metadata else None,
                latency=latency,
                status=True
            ))
            info("Synchronous request finalized successfully.", "[GoogleHandler]")
            
            return await self.response_parser(response)
            
        except asyncio.TimeoutError:
            error(f"Google API request timed out after {timeout_seconds} seconds", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            raise ValueError(f"API request timed out after {timeout_seconds} seconds")
        except Exception as e:
            error(f"An error occurred during sync handle: {e}", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            return Response(type="error", error=str(e))
    async def stream_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[GoogleHandler]")
        Provider_messages = await self.message_complier(messages)

        # Get timeout from environment variable (default: 60 seconds for streaming)
        timeout_seconds = int(os.getenv("API_STREAM_TIMEOUT_SECONDS", "60"))
        debug(f"Using streaming API timeout: {timeout_seconds} seconds", "[GoogleHandler]")

        latency = time.time()
        first_chunk_received = False
        try:
            debug("Sending streaming request to Google API.", "[GoogleHandler]")
            
            # Convert tools to Google format
            google_tools = None
            if tools:
                google_tools = []
                for tool in tools:
                    # Convert our Tool model to Google's FunctionDeclaration
                    google_tool = genai.types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description or "",
                        parameters=tool.parameters or {}
                    )
                    google_tools.append(google_tool)
            
            # Add timeout to the streaming API call
            stream_response = await asyncio.wait_for(
                self.model.generate_content_async(
                    **Provider_messages, 
                    stream=True,
                    tools=google_tools if google_tools else None
                ),
                timeout=timeout_seconds
            )
            
            async for chunk in stream_response:
                if chunk and chunk.parts:
                    if not first_chunk_received:
                        latency = time.time() - latency
                        first_chunk_received = True
                    
                    # Process each part in the chunk
                    for part in chunk.parts:
                        if hasattr(part, 'text') and part.text:
                            # Handle text content - same format as OpenAI
                            debug(f"Received stream chunk: {part.text[:50]}...", "[GoogleHandler]")
                            yield f"data: {part.text}\n\n"
                        elif hasattr(part, 'function_call') and part.function_call:
                            # Handle function calls - convert to OpenAI format for consistency
                            tool_calls_data = {
                                "tool_calls": [{
                                    "id": f"call_{hash(str(part.function_call))}",
                                    "type": "function",
                                    "function": {
                                        "name": part.function_call.name,
                                        "arguments": json.dumps(dict(part.function_call.args)) if part.function_call.args else "{}"
                                    }
                                }]
                            }
                            debug(f"Received function call: {part.function_call.name}", "[GoogleHandler]")
                            yield f"data: {json.dumps(tool_calls_data)}\n\n"
                else:
                    warning("Received an empty or invalid chunk in stream.", "[GoogleHandler]")
                response = chunk  # Keep the last chunk to get usage metadata
            
            info("Streaming finished.", "[GoogleHandler]")

        except asyncio.TimeoutError:
            error(f"Google streaming API request timed out after {timeout_seconds} seconds", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=f"Request timed out after {timeout_seconds} seconds"
            ))
            yield f"data: Request timed out after {timeout_seconds} seconds\n\n"
        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                latency=None,
                status=False,
                error_message=str(e)
            ))
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id,
                input_tokens=response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') and response.usage_metadata else None,
                output_tokens=response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') and response.usage_metadata else None,
                reasoning_tokens=response.usage_metadata.cached_content_token_count if hasattr(response, 'usage_metadata') and response.usage_metadata else None,
                latency=latency,
                status=True
            ))
            info("Full streaming request finalized successfully.", "[GoogleHandler]")
            yield "data: [DONE]\n\n"

    @staticmethod
    def get_models() -> list[str]:
        """
        Returns a list of available models from Google.
        """
        debug("Fetching available models from Google.", "[GoogleHandler]")
        try:
            models_info = genai.list_models()
            model_names = [m.name.split('/')[-1] for m in models_info if 'generateContent' in m.supported_generation_methods]
            debug(f"Found models: {model_names}", "[GoogleHandler]")
            return model_names
        except Exception as e:
            error(f"Failed to fetch models from Google: {e}", "[GoogleHandler]")
            return [] 