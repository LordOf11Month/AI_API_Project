from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    messages: List[dict]
    provider: str
    model: str
    stream: bool = False
    parameters: dict = {}

def chat_request(request: ChatRequest):
    pass