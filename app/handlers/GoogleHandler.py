
import google.generativeai as genai
from typing import Dict, Any, AsyncIterable
from uuid import UUID
import os
from app.handlers.BaseHandler import BaseHandler
from app.DB_connection.request_manager import finalize_request
from app.DB_connection.chat_manager import chat_history
from app.utils.console_logger import info, warning, error, debug

class GoogleHandler(BaseHandler):
    """
    Handles requests for Google's AI models.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: str | None):
        super().__init__(model_name, generation_config, system_instruction)
        
        # Configure the generative AI model
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=self.system_instruction
        )
        debug(f"Google AI model '{self.model_name}' initialized.", "[GoogleHandler]")

    async def chat_complier(self, user_prompt: str, chat_id: UUID | None) -> list[Dict[str, str]]:
        """
        Compiles the chat history and the new user prompt into a list of messages
        formatted for the AI model.
        """
        debug(f"Compiling chat for chat_id: {chat_id}", "[GoogleHandler]")
        history = []
        if chat_id:
            raw_history = await chat_history(chat_id)
            if raw_history:
                debug(f"Found {len(raw_history)} messages in chat history.", "[GoogleHandler]")
                for record in raw_history:
                    # Append user prompt
                    history.append({'role': 'user', 'parts': [record.user_prompt]})
                    # Append model response
                    history.append({'role': 'model', 'parts': [record.model_response]})
            else:
                warning(f"No history found for chat_id: {chat_id}", "[GoogleHandler]")
        
        # Add the latest user prompt
        history.append({'role': 'user', 'parts': [user_prompt]})
        debug(f"Chat compiled. Total messages: {len(history)}", "[GoogleHandler]")
        return history

    async def sync_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> Dict[str, Any]:
        """
        Handles a non-streaming (synchronous) request.
        """
        info(f"Handling synchronous request for model: {self.model_name}", "[GoogleHandler]")
        messages = await self.chat_complier(user_prompt, chat_id)
        
        try:
            debug("Sending request to Google API.", "[GoogleHandler]")
            response = await self.model.generate_content_async(messages)
            
            if not response.parts:
                warning("Received an empty response from Google API.", "[GoogleHandler]")
                model_response_content = "No content returned."
            else:
                model_response_content = ''.join(part.text for part in response.parts)
                debug(f"Received synchronous response: {model_response_content[:100]}...", "[GoogleHandler]")

            debug(f"finalizing request for request_id: {request_id}", "[GoogleHandler]")
            await finalize_request(request_id, model_response_content)
            info("Synchronous request finalized successfully.", "[GoogleHandler]")
            
            return {"response": model_response_content}
            
        except Exception as e:
            error(f"An error occurred during sync handle: {e}", "[GoogleHandler]")
            raise

    async def stream_handle(self, user_prompt: str, chat_id: UUID | None, request_id: UUID) -> AsyncIterable[Dict[str, Any]]:
        """
        Handles a streaming request.
        """
        info(f"Handling streaming request for model: {self.model_name}", "[GoogleHandler]")
        messages = await self.chat_complier(user_prompt, chat_id)
        
        full_response = ""
        try:
            debug("Sending streaming request to Google API.", "[GoogleHandler]")
            async for chunk in await self.model.generate_content_async(messages, stream=True):
                if chunk and chunk.parts:
                    chunk_text = ''.join(part.text for part in chunk.parts)
                    full_response += chunk_text
                    debug(f"Received stream chunk: {chunk_text[:50]}...", "[GoogleHandler]")
                    yield f"data: {chunk_text}\n\n"
                else:
                    warning("Received an empty or invalid chunk in stream.", "[GoogleHandler]")
            
            info("Streaming finished.", "[GoogleHandler]")

        except Exception as e:
            error(f"An error occurred during stream handle: {e}", "[GoogleHandler]")
            yield f"data: An error occurred: {str(e)}\n\n"
        
        finally:
            debug(f"finalizing full streaming request for request_id: {request_id}", "[GoogleHandler]")
            await finalize_request(request_id, full_response)
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