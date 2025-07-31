
import time
import google.generativeai as genai
from typing import Dict, Any, AsyncIterable
from uuid import UUID
import asyncio
import os
from app.handlers.BaseHandler import BaseHandler
from app.DB_connection.request_manager import finalize_request
from app.models.DataModels import RequestFinal, message
from app.utils.console_logger import info, warning, error, debug

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

    async def sync_handle(self, messages: list[message], request_id: UUID) -> Dict[str, Any]:
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
            
            # Add timeout to the API call
            response = await asyncio.wait_for(
                self.model.generate_content_async(Provider_messages),
                timeout=timeout_seconds
            )
            
            latency = time.time() - latency
            
            if not response.parts:
                warning("Received an empty response from Google API.", "[GoogleHandler]")
                model_response_content = "No content returned."
            else:
                model_response_content = ''.join(part.text for part in response.parts)
                debug(f"Received synchronous response: {model_response_content[:100]}...", "[GoogleHandler]")

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
            
            return model_response_content
            
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
            raise
    async def stream_handle(self, messages: list[message], request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[GoogleHandler]")
        Provider_messages = await self.message_complier(messages)

        # Get timeout from environment variable (default: 60 seconds for streaming)
        timeout_seconds = int(os.getenv("API_STREAM_TIMEOUT_SECONDS", "60"))
        debug(f"Using streaming API timeout: {timeout_seconds} seconds", "[GoogleHandler]")

        latency = time.time()
        response = None
        first_chunk_received = False
        try:
            debug("Sending streaming request to Google API.", "[GoogleHandler]")
            
            # Add timeout to the streaming API call
            stream_response = await asyncio.wait_for(
                self.model.generate_content_async(Provider_messages, stream=True),
                timeout=timeout_seconds
            )
            
            async for chunk in stream_response:
                if chunk and chunk.parts:
                    if not first_chunk_received:
                        latency = time.time() - latency
                        first_chunk_received = True
                    chunk_text = ''.join(part.text for part in chunk.parts)
                    debug(f"Received stream chunk: {chunk_text[:50]}...", "[GoogleHandler]")
                    yield f"data: {chunk_text}\n\n"
                else:
                    warning("Received an empty or invalid chunk in stream.", "[GoogleHandler]")
                response = chunk  # Keep the last chunk to get usage metadata
            
            info("Streaming finished.", "[GoogleHandler]")

        except asyncio.TimeoutError:
            error(f"Google streaming API request timed out after {timeout_seconds} seconds", "[GoogleHandler]")
            yield f"data: Request timed out after {timeout_seconds} seconds\n\n"
        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[GoogleHandler]")
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[GoogleHandler]")
            await finalize_request(RequestFinal(
                request_id=request_id, 
                input_tokens=response.usage_metadata.prompt_token_count if response and response.usage_metadata else None,
                output_tokens=response.usage_metadata.candidates_token_count if response and response.usage_metadata else None,
                reasoning_tokens=response.usage_metadata.cached_content_token_count if response and response.usage_metadata else None,
                latency=None,
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