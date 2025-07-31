from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey, JSON, BOOLEAN, TEXT, SMALLINT, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import  relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PyEnum

Base = declarative_base()

class Provider(PyEnum):
    google = 'google'
    openai = 'openai'
    anthropic = 'anthropic'
    deepseek = 'deepseek'

class Role(PyEnum):
    user = 'user'
    assistant = 'assistant'
    system = 'system'
    tool = 'tool'

class Client(Base):
    __tablename__ = 'clients'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    api_keys = relationship("APIKey", back_populates="client")

class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    name = Column(String(255),primary_key=True, nullable=False)
    prompt = Column(TEXT, nullable=False)
    tenant_fields = Column(JSON, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)

class Chat(Base):
    __tablename__ = 'chats'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.utcnow)
    client = relationship("Client")
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = 'messages'
    index = Column(Integer, primary_key=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey('chats.id', ondelete='CASCADE'))
    role = Column(Enum(Role, name='role_enum', native_enum=False))
    content = Column(TEXT, nullable=False)
    chat = relationship("Chat", back_populates="messages")

    __table_args__ = (
    Index('idx_messages_chat_id', 'chat_id'),
    Index('idx_messages_index', 'index'),
    )
class Request(Base):
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
    client = relationship("Client")
    latency = Column(Float)


class APIKey(Base):
    __tablename__ = 'api_keys'
    api_key = Column(UUID(as_uuid=True), primary_key=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    provider = Column(Enum(Provider, name='provider_enum', native_enum=False))
    client = relationship("Client", back_populates="api_keys") 