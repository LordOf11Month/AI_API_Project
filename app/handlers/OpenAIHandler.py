from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import finalize_request
from app.DB_connection.chat_manager import chat_history
from app.utils.console_logger import info, warning, error, debug


class OpenAIHandler(BaseHandler):
    """
    Handler for OpenAI's GPT models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncOpenAI()
        debug(f"OpenAI client initialized for model '{self.model_name}'.", "[OpenAIHandler]")

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        try:
            info(f"Handling synchronous request for model: {self.model_name}", "[OpenAIHandler]")
            debug(f"Request ID: {request_id}", "[OpenAIHandler]")
            
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            if self.system_instruction:
                formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})
            
            try:
                debug("Sending request to OpenAI API.", "[OpenAIHandler]")
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config
                )
                debug("Received synchronous response from API.", "[OpenAIHandler]")
            except asyncio.CancelledError:
                warning("Request was cancelled during API call", "[OpenAIHandler]")
                asyncio.create_task(finalize_request(ResponseLog(
                    request_id=request_id,
                    response="Request cancelled",
                    input_tokens=0,
                    output_tokens=0,
                    status=False,
                    error_message="Request was cancelled during processing"
                )))
                raise

            response_content = response.choices[0].message.content
            debug(f"Extracted response content: {response_content[:100]}...", "[OpenAIHandler]")

            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                response=response_content,
                status=response.choices[0].finish_reason == "stop",
            )))

            info("Synchronous response processed and logged.", "[OpenAIHandler]")
            return {"response": response_content}

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                error(f"An error occurred during sync handle: {e}", "[OpenAIHandler]")
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
        info(f"Handling streaming request for model: {self.model_name}", "[OpenAIHandler]")
        debug(f"Request ID: {request_id}", "[OpenAIHandler]")
        
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        if self.system_instruction:
            formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})

        full_response = ""
        try:
            debug("Sending streaming request to OpenAI API.", "[OpenAIHandler]")
            response_stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                **self.generation_config,
                stream=True
            )
            
            debug("Processing stream chunks...", "[OpenAIHandler]")
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    debug(f"Received stream chunk: {content[:50]}...", "[OpenAIHandler]")
                yield {"response": content}
            
            info("Streaming finished. Logging full response.", "[OpenAIHandler]")
            asyncio.create_task(finalize_request(ResponseLog(
                request_id=request_id,
                response=full_response,
                input_tokens=0, 
                output_tokens=0,
                status=True,
            )))

        except asyncio.CancelledError:
            warning("Stream was cancelled during processing", "[OpenAIHandler]")
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
            error(f"An error occurred during stream handle: {e}", "[OpenAIHandler]")
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
    
    @staticmethod
    async def chat_complier(userprompt:str,chat_id:UUID | None) -> list[Dict[str, str]]:
        """
        This method is used to compile the user prompt into a list of messages for the model.
        """
        debug(f"Compiling chat for chat_id: {chat_id}", "[OpenAIHandler]")
        history = await chat_history(chat_id)
        if history:
            debug(f"Found {len(history)} messages in chat history.", "[OpenAIHandler]")
        else:
            warning(f"No history found for chat_id: {chat_id}", "[OpenAIHandler]")

        formatted_messages = []
        for message in history:
            formatted_messages.append({"role": "user", "content": message["request"]})
            formatted_messages.append({"role": "assistant", "content": message["response"]})
        
        formatted_messages.append({"role": "user", "content": userprompt})
        debug(f"Chat compiled. Total messages: {len(formatted_messages)}", "[OpenAIHandler]")
        return formatted_messages
    
    