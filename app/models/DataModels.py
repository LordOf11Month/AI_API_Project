from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.DBModels import Role


class RequestInit(BaseModel):
    client_id: UUID
    model_name: str 
    created_at: datetime
    provider: str
    is_client_api: bool


class RequestFinal(BaseModel):
    request_id: UUID
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    status: bool
    latency: float
    error_message: Optional[str] = None

class SystemPrompt(BaseModel):
    template_name: str
    tenants: Dict[str, Any] = Field(default_factory=dict)

class BaseAPIRequest(BaseModel):
    provider: str
    model: str
    systemPrompt: SystemPrompt
    parameters: Dict[str, Any] = Field(default_factory=dict)
    stream: bool = False

class GenerateRequest(BaseAPIRequest):
    messages: list[message]

class message(BaseModel):
    role: Role
    content: str

class ChatRequest(BaseAPIRequest):
    message: message
    chat_id: Optional[UUID] = None

class BaseRequest(BaseAPIRequest):
    messages: Optional[list[message]] = None
    user_prompt: Optional[str] = None
    chat_id: Optional[UUID] = None

class ClientCredentials(BaseModel):
    email: str
    password: str


class PromptTemplateCreate(BaseModel):
    name: str
    prompt: str
    tenant_fields: list[str] = []
