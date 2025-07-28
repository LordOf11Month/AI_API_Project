from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from uuid import UUID


@dataclass
class RequestLog:
    chat_id: UUID
    user_prompt: str
    model_name: str
    system_prompt: Any  # Typically SystemPrompt from app.routers.Dispatcher
    created_at: datetime


@dataclass
class ResponseLog:
    request_id: UUID
    input_tokens: int
    output_tokens: int
    response: str
    status: bool
    error_message: str | None = None

@dataclass
class SystemPrompt:
    template: str
    tenants: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APIRequest:
    provider: str
    model: str
    systemPrompt: SystemPrompt
    userprompt: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    stream: bool = False
    chatid: UUID | None = None
