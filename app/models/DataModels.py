"""
Pydantic Data Models

This module defines the Pydantic models used for data validation, serialization,
and deserialization in the API. These models ensure that incoming request data
is correctly formatted and that outgoing responses adhere to a consistent schema.

Key Model Categories:
- API Requests: Models for /generate, /chat, /signup, /token, etc.
- API Responses: Models for returning data from endpoints
- Internal Data Structures: Models for passing data between system components

Author: Ramazan Seçilmiş
Version: 1.0.0
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.DBModels import Role, Provider


class RequestInit(BaseModel):
    """
    Model for initializing a request in the database.
    """
    client_id: UUID
    model_name: str 
    created_at: datetime
    provider: Provider
    is_client_api: bool


class RequestFinal(BaseModel):
    """
    Model for finalizing a request in the database with token counts and status.
    """
    request_id: UUID
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    status: bool
    latency: Optional[float] = None
    error_message: Optional[str] = None

class SystemPrompt(BaseModel):
    """
    Model for defining a system prompt with a template and variables.
    """
    template_name: str
    tenants: Dict[str, Any] = Field(default_factory=dict)

class BaseAPIRequest(BaseModel):
    """
    Base model for all AI generation API requests.
    """
    provider: Provider
    model: str
    tools: Optional[list[Tool]] = None
    systemPrompt: SystemPrompt
    parameters: Dict[str, Any] = Field(default_factory=dict)
    stream: bool = False

class GenerateRequest(BaseAPIRequest):
    """
    Model for one-shot generation requests (/api/generate).
    """
    messages: list[message]

class message(BaseModel):
    """
    Model representing a single message in a conversation.
    """
    role: Role
    content: str
    

class ChatRequest(BaseAPIRequest):
    """
    Model for conversational chat requests (/api/chat).
    """
    message: message
    chat_id: Optional[UUID] = None


class ClientCredentials(BaseModel):
    """
    Model for client signup and token generation.
    """
    email: str
    password: str
    expr: Optional[Dict[str, int]] = None

class PromptTemplateCreate(BaseModel):
    """
    Model for creating or updating a prompt template.
    """
    name: str
    prompt: str
    tenant_fields: list[str] = []

class APIKeyCreate(BaseModel):
    """
    Model for creating a new client-specific API key.
    """
    provider: Provider
    api_key: str

class APIKeyUpdate(BaseModel):
    """
    Model for updating an existing client-specific API key.
    """
    api_key: str
    provider: Provider

class APIKeyResponse(BaseModel):
    """
    Model for returning masked API key information.
    """
    provider: Provider
    masked_api_key: str
    created_at: Optional[datetime] = None

class Tool(BaseModel):
    """
    Model representing a function tool for the AI model, matching OpenAI's format.
    """
    name: str
    """The name of the function to call."""

    parameters: Optional[Dict[str, object]] = None
    """A JSON schema object describing the parameters of the function."""

    strict: Optional[bool] = None
    """Whether to enforce strict parameter validation. Default `true`."""

    type: Literal["function"]
    """The type of the function tool. Always `function`."""

    description: Optional[str]
    """A description of the function.

    Used by the model to determine whether or not to call the function.
    """

class Response(BaseModel):
    """
    Unified response model for returning AI-generated content, function calls, or errors.
    """
    type: Literal["message", "function_call", "error"]
    content: Optional[str] = None
    function_name: Optional[str] = None
    function_args: Optional[Dict[str, str]] = None
    chat_id: Optional[UUID] = None