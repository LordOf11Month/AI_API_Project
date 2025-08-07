"""
SQLAlchemy Database Models

This module defines the SQLAlchemy ORM models that represent the database schema
for the Unified AI API. These models are used to create, read, update, and delete
records in the database.

Key Models:
- Client: Represents a registered user account
- PromptTemplate: Stores reusable prompt templates
- Chat: Represents a single conversation session
- Message: Stores individual messages within a chat
- Request: Tracks AI generation requests for logging and analytics
- APIKey: Stores client-specific API keys for different providers

Enums:
- Provider: Defines the supported AI providers (Google, OpenAI, Anthropic, DeepSeek)
- Role: Defines the roles in a conversation (user, assistant, system, tool)

Relationships:
- Client to APIKey (one-to-many)
- Client to Chat (one-to-many)
- Chat to Message (one-to-many)

Author: Ramazan Seçilmiş
Version: 1.0.0
"""

from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey, JSON, BOOLEAN, TEXT, SMALLINT, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import  relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PyEnum

Base = declarative_base()

class Provider(PyEnum):
    """
    Enum for supported AI providers.
    """
    google = 'google'
    openai = 'openai'
    anthropic = 'anthropic'
    deepseek = 'deepseek'

class Role(PyEnum):
    """
    Enum for message roles in a conversation.
    """
    user = 'user'
    assistant = 'assistant'
    system = 'system'
    tool = 'tool'

class Client(Base):
    """
    Represents a registered client account.
    """
    __tablename__ = 'clients'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to APIKey model
    api_keys = relationship("APIKey", back_populates="client")

class PromptTemplate(Base):
    """
    Stores reusable prompt templates for consistent AI generation.
    """
    __tablename__ = 'prompt_templates'
    name = Column(String(255),primary_key=True, nullable=False)
    prompt = Column(TEXT, nullable=False)
    tenant_fields = Column(JSON, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)

class Chat(Base):
    """
    Represents a single conversation session.
    """
    __tablename__ = 'chats'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships to Client and Message models
    client = relationship("Client")
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    """
    Represents a single message within a chat session.
    """
    __tablename__ = 'messages'
    index = Column(Integer, primary_key=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey('chats.id', ondelete='CASCADE'))
    role = Column(Enum(Role, name='role_enum', native_enum=False))
    content = Column(TEXT, nullable=False)
    
    # Relationship to Chat model
    chat = relationship("Chat", back_populates="messages")

    # Database indexes for faster queries
    __table_args__ = (
    Index('idx_messages_chat_id', 'chat_id'),
    Index('idx_messages_index', 'index'),
    )
class Request(Base):
    """
    Tracks AI generation requests for logging, analytics, and billing.
    """
    __tablename__ = 'requests'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    model_name = Column(TEXT, nullable=False)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    reasoning_tokens = Column(Integer)
    status = Column(BOOLEAN, default=False)
    error_message = Column(TEXT, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_client_api = Column(BOOLEAN, default=False)
    model_provider = Column(Enum(Provider, name='provider_enum', native_enum=False))
    
    # Relationship to Client model
    client = relationship("Client")
    latency = Column(Float)


class APIKey(Base):
    """
    Stores client-specific, encrypted API keys for different AI providers.
    """
    __tablename__ = 'api_keys'
    api_key = Column(String(255), primary_key=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    provider = Column(Enum(Provider, name='provider_enum', native_enum=False))
    
    # Relationship to Client model
    client = relationship("Client", back_populates="api_keys") 