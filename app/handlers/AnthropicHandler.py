from typing import Union, AsyncIterable, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import finalize_request
from app.DB_connection.chat_manager import chat_history
import os
from app.utils.console_logger import info, warning, error, debug


class AnthropicHandler(BaseHandler):
    """
    Handler for Anthropic's Claude models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncAnthropic()
        debug(f"Anthropic client initialized for model '{self.model_name}'.", "[AnthropicHandler]")

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        try:
            info(f"Handling synchronous request for model: {self.model_name}", "[AnthropicHandler]")
            debug(f"Request ID: {request_id}", "[AnthropicHandler]")

            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            
            try:
                debug("Sending request to Anthropic API.", "[AnthropicHandler]")
                response = await self.client.messages.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    system=self.system_instruction,
                    **self.generation_config
                )
                debug("Received synchronous response from API.", "[AnthropicHandler]")
            except asyncio.CancelledError:
                warning("Request was cancelled during API call", "[AnthropicHandler]")
                asyncio.create_task(finalize_request(ResponseLog(
                    request_id=request_id,
                    response="Request cancelled",
                    input_tokens=0,
                    output_tokens=0,
                    status=False,
                    error_message="Request was cancelled during processing"
                )))
                raise

            response_content = response.content[0].text
            debug(f"Extracted response content: {response_content[:100]}...", "[AnthropicHandler]")

            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                response=response_content,
                status=response.stop_reason == "end_turn",
            )))

            info("Synchronous response processed and logged.", "[AnthropicHandler]")
            return {"response": response_content}

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                error(f"An error occurred during sync handle: {e}", "[AnthropicHandler]")
                asyncio.create_task(finalize_request(ResponseLog(
                    request_id=request_id,
                    response="",
                    input_tokens=0,
                    output_tokens=0,
                    status=False,
                    error_message=str(e)
                )))
            raise

    async def stream_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        info(f"Handling streaming request for model: {self.model_name}", "[AnthropicHandler]")
        debug(f"Request ID: {request_id}", "[AnthropicHandler]")
        
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        
        full_response = ""
        try:
            debug("Sending streaming request to Anthropic API.", "[AnthropicHandler]")
            async with self.client.messages.stream(
                model=self.model_name,
                messages=formatted_messages,
                system=self.system_instruction,
                **self.generation_config
            ) as response_stream:
                debug("Processing stream chunks...", "[AnthropicHandler]")
                async for chunk in response_stream.text_stream:
                    full_response += chunk
                    debug(f"Received stream chunk: {chunk[:50]}...", "[AnthropicHandler]")
                    yield {"response": chunk}
                
                final_message = await response_stream.get_final_message()
            
            info("Streaming finished. Logging full response.", "[AnthropicHandler]")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=final_message.usage.input_tokens,
                output_tokens=final_message.usage.output_tokens,
                status=True,
            )))

        except asyncio.CancelledError:
            warning("Stream was cancelled during processing", "[AnthropicHandler]")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=0,
                output_tokens=0,
                status=False,
                error_message="Stream was cancelled during processing"
            )))
            raise

        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[AnthropicHandler]")
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
        debug("Fetching available models for Anthropic.", "[AnthropicHandler]")
        try:
            models = [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
            debug(f"Found models: {models}", "[AnthropicHandler]")
            return models
        except Exception as e:
            error(f"Failed to fetch models for Anthropic: {e}", "[AnthropicHandler]")
            return []
        
    @staticmethod
    async def chat_complier(userprompt:str,chat_id:UUID | None) -> list[Dict[str, str]]:
        """
        This method is used to compile the user prompt into a list of messages for the model.
        """
        debug(f"Compiling chat for chat_id: {chat_id}", "[AnthropicHandler]")
        history = await chat_history(chat_id)
        if history:
            debug(f"Found {len(history)} messages in chat history.", "[AnthropicHandler]")
        else:
            warning(f"No history found for chat_id: {chat_id}", "[AnthropicHandler]")
            
        formatted_messages = []
        for message in history:
            formatted_messages.append({"role": "user", "content": message["request"]})
            formatted_messages.append({"role": "assistant", "content": message["response"]})
        
        formatted_messages.append({"role": "user", "content": userprompt})
        debug(f"Chat compiled. Total messages: {len(formatted_messages)}", "[AnthropicHandler]")
        return formatted_messages
        