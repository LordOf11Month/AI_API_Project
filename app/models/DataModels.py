from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class RequestLog(BaseModel):
    client_id: UUID
    chat_id: Optional[UUID] = None
    user_prompt: str
    model_name: str
    system_prompt: Any  # Typically SystemPrompt from app.routers.Dispatcher
    created_at: datetime
    provider: str
    is_client_api: bool


class ResponseLog(BaseModel):
    request_id: UUID
    input_tokens: int
    output_tokens: int
    response: str
    status: bool
    error_message: Optional[str] = None

class SystemPrompt(BaseModel):
    template_name: str
    tenants: Dict[str, Any] = Field(default_factory=dict)

class APIRequest(BaseModel):
    provider: str
    model: str
    systemPrompt: SystemPrompt
    userprompt: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    chatid: Optional[UUID] = None


class ClientCredentials(BaseModel):
    email: str
    password: str


class PromptTemplateCreate(BaseModel):
    name: str
    prompt: str
    tenant_fields: list[str] = []
