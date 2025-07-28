from typing import Union, AsyncIterable, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_logger import log_response
from app.DB_connection.chat_manager import chat_history


class AnthropicHandler(BaseHandler):
    """
    Handler for Anthropic's Claude models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncAnthropic()

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                messages=formatted_messages,
                system=self.system_instruction,
                **self.generation_config
            )
            asyncio.create_task(log_response(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                response=response.content[0].text,
                status=response.stop_reason == "end_turn",
            )))
            return response
        except Exception as e:
            print(f"Error handling Anthropic request: {e}")
            return f"An error occurred: {e}"

    async def stream_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        
        async def stream_and_finalize():
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            full_response = ""
            try:
                async with self.client.messages.stream(
                    model=self.model_name,
                    messages=formatted_messages,
                    system=self.system_instruction,
                    **self.generation_config
                ) as response_stream:
                    async for chunk in response_stream.text_stream:
                        full_response += chunk
                        yield chunk
                    
                    final_message = await response_stream.get_final_message()
                
                # After the stream is complete, log the response
                await log_response(ResponseLog(
                    request_id=request_id,
                    response=full_response,
                    input_tokens=final_message.usage.input_tokens,
                    output_tokens=final_message.usage.output_tokens,
                    status=True,  # Assuming success if stream completes
                ))

            except Exception as e:
                print(f"Error handling Anthropic stream: {e}")
                await log_response(ResponseLog(
                    request_id=request_id,
                    response=full_response,
                    error_message=str(e),
                    status=False,
                ))
                yield f"An error occurred: {e}"

        return stream_and_finalize()

    @staticmethod
    def get_models() -> list[str]:
        """`
        Get a list of available Anthropic models.
        """
        try:
            # Note: Anthropic SDK doesn't have a direct equivalent of OpenAI's `models.list()`.
            # Officially, they recommend referring to their documentation for model names.
            # For this reason, we'll return a static list of commonly used models.
            # You can update this list as new models are released.
            return [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
        except Exception as e:
            print(f"Error getting Anthropic models: {e}")
            return []
        
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
        