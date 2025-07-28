from abc import ABC, abstractmethod
from typing import Union, AsyncIterable, Dict, Any, Optional
from uuid import UUID

class BaseHandler(ABC):
    """
    An abstract base class for AI model handlers. It defines a common interface
    for handling generation requests.
    """
    def __init__(self, model_name: str, generation_config: Dict[str, Any], system_instruction: Optional[str]):
        self.model_name = model_name
        self.generation_config = generation_config
        self.system_instruction = system_instruction

    @abstractmethod
    async def sync_handle(self, messages: list[Dict[str, str]],request_id:UUID) -> Dict[str, Any]:
        """
        Processes a prompt and returns the model's response.

        This method must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def stream_handle(self, messages: list[Dict[str, str]],request_id:UUID) -> AsyncIterable[Dict[str, Any]]:
        """
        Processes a prompt and returns the model's response as an async iterable of strings.

        This method must be implemented by subclasses.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_models() -> list[str]:
        """
        Returns a list of available models for this provider.
        This should be implemented as a static method by subclasses.
        """
        pass