"""
Abstract Base Class for AI Handlers

This module defines the abstract base class (ABC) for all AI provider handlers.
It establishes a common interface that all concrete handler implementations must
follow, ensuring consistency and interchangeability between providers.

The BaseHandler enforces the implementation of key methods for handling synchronous
and streaming generation, retrieving available models, and compiling messages.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""
from abc import ABC, abstractmethod
from typing import AsyncIterable, Dict, Any, Optional
from uuid import UUID

from app.models.DataModels import message, Tool, Response

class BaseHandler(ABC):
    """
    An abstract base class for AI model handlers. It defines a common interface
    for handling generation requests, abstracting provider-specific details.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str], API_KEY: str):
        """
        Initializes the handler with common configuration.
        
        Args:
            model_name (str): The specific model to use for generation.
            generation_config (Dict[str, Any]): Provider-specific generation parameters.
            system_instruction (Optional[str]): System prompt or instruction for the model.
            API_KEY (str): The API key for the provider.
        """
        self.model_name = model_name
        self.generation_config = generation_config
        self.system_instruction = system_instruction
        self.API_KEY = API_KEY

    @abstractmethod
    async def sync_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> Response:
        """
        Processes a non-streaming (synchronous) generation request.
        
        This method must be implemented by subclasses.
        
        Args:
            messages (list[message]): The list of messages in the conversation.
            request_id (UUID): The unique ID for tracking the request.
            tools (Optional[list[Tool]]): A list of function tools available to the model.
            
        Returns:
            Response: A unified response object containing the result.
        """
        pass

    @abstractmethod
    async def stream_handle(self, messages: list[message], request_id: UUID, tools: Optional[list[Tool]] = None) -> AsyncIterable[bytes]:
        """
        Processes a streaming generation request.
        
        This method must be implemented by subclasses.
        
        Args:
            messages (list[message]): The list of messages in the conversation.
            request_id (UUID): The unique ID for tracking the request.
            tools (Optional[list[Tool]]): A list of function tools available to the model.
            
        Returns:
            AsyncIterable[bytes]: An async iterable yielding response chunks.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_models() -> list[str]:
        """
        Returns a list of available models for the provider.
        
        This should be implemented as a static method by subclasses.
        """
        pass

    @staticmethod
    @abstractmethod
    def message_complier(messages: list[message]) -> any:
       """
       Compiles a list of messages into the provider-specific format.
       
       This method must be implemented by subclasses.
       """
       pass
