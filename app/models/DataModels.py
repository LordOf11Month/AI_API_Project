from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.DBModels import Role, Provider


class RequestInit(BaseModel):
    client_id: UUID
    model_name: str 
    created_at: datetime
    provider: Provider
    is_client_api: bool


class RequestFinal(BaseModel):
    request_id: UUID
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    status: bool
    latency: Optional[float] = None
    error_message: Optional[str] = None

class SystemPrompt(BaseModel):
    template_name: str
    tenants: Dict[str, Any] = Field(default_factory=dict)

class BaseAPIRequest(BaseModel):
    provider: Provider
    model: str
    tools: Optional[list[Tool]] = None
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


class ClientCredentials(BaseModel):
    email: str
    password: str
    expr: Optional[Dict[str, int]] = None

class PromptTemplateCreate(BaseModel):
    name: str
    prompt: str
    tenant_fields: list[str] = []

class APIKeyCreate(BaseModel):
    provider: Provider
    api_key: str

class APIKeyUpdate(BaseModel):
    api_key: str
    provider: Provider

class APIKeyResponse(BaseModel):
    provider: Provider
    masked_api_key: str
    created_at: Optional[datetime] = None

class ToolFunction(BaseModel):
    name: str
    """The name of the function to call."""
    
    description: Optional[str] = None
    """A description of what the function does, used by the model to choose when and how to call the function."""
    
    parameters: Optional[Dict[str, object]] = None
    """The parameters the functions accepts, described as a JSON Schema object."""
    
    strict: Optional[bool] = None
    """Whether to enable strict schema adherence when generating the function call."""

class Tool(BaseModel):
    type: Literal["function"] = "function"
    """The type of the tool. Currently, only `function` is supported."""
    
    function: ToolFunction
    """The function definition."""