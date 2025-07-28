from typing import Union, AsyncIterable, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from app.handlers.BaseHandler import BaseHandler
import asyncio
from uuid import UUID
from app.models.DataModels import ResponseLog
from app.DB_connection.request_manager import log_response
from app.DB_connection.chat_manager import chat_history


class OpenAIHandler(BaseHandler):
    """
    Handler for OpenAI's GPT models.
    """

    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        super().__init__(model_name, generation_config, system_instruction)
        self.client = AsyncOpenAI()

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.
        """
        formatted_messages = await self.chat_complier(user_prompt, chat_id)
        if self.system_instruction:
            formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})

        try:
            # Note: The 'chat.completions' endpoint is the current standard for all modern
            # OpenAI models (e.g., GPT-4, GPT-4o), even for single-turn, non-chat requests.
            # This is the recommended approach by OpenAI for accessing their latest models.
            #thats why I use this endpoint
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                **self.generation_config
            )
            asyncio.create_task(log_response(ResponseLog(
                request_id=request_id,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                response=response.choices[0].message.content,
                status=response.choices[0].finish_reason == "stop",
            )))
            return response
        except Exception as e:
            print(f"Error handling OpenAI request: {e}")
            return f"An error occurred: {e}"
        
    async def stream_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        
        async def stream_and_finalize():
            formatted_messages = await self.chat_complier(user_prompt, chat_id)
            if self.system_instruction:
                formatted_messages.insert(0, {"role": "system", "content": self.system_instruction})

            full_response = ""
            try:
                response_stream = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    **self.generation_config,
                    stream=True
                )
                
                async for chunk in response_stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                    yield chunk
                
                # After the stream is complete, log the response
                await log_response(ResponseLog(
                    request_id=request_id,
                    response=full_response,
                    input_tokens=None, # Not available for streaming
                    output_tokens=None, # Not available for streaming
                    status=True,  # Assuming success if stream completes
                ))

            except Exception as e:
                print(f"Error handling OpenAI stream: {e}")
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
        """
        Return all available OpenAI models. 
        This is a static method so it can be called without creating an instance.
        """
        try:
            client = OpenAI()
            return [model.id for model in client.models.list()]
        except Exception as e:
            print(f"Error getting OpenAI models: {e}")
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
    
    