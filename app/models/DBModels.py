from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, BOOLEAN, TEXT, SMALLINT, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import  relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    api_keys = relationship("APIKey", back_populates="client")

class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    prompt = Column(TEXT, nullable=False)
    version = Column(SMALLINT, default=1)
    tenant_fields = Column(JSON, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)

class Chat(Base):
    __tablename__ = 'chats'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.utcnow)
    client = relationship("Client")
    requests = relationship("Request", back_populates="chat")

class Request(Base):
    __tablename__ = 'requests'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey('chats.id', ondelete='SET NULL'))
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    prompt_template_id = Column(UUID(as_uuid=True), ForeignKey('prompt_templates.id'))
    system_prompt_tenants = Column(JSON, default=None)
    template_version = Column(SMALLINT, default=1)
    model_name = Column(TEXT, nullable=False)
    request = Column(TEXT, nullable=False)
    response = Column(TEXT, nullable=False)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    status = Column(BOOLEAN)
    error_message = Column(TEXT, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="requests")
    client = relationship("Client")
    prompt_template = relationship("PromptTemplate")

class APIKey(Base):
    __tablename__ = 'api_keys'
    api_key = Column(UUID(as_uuid=True), primary_key=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    provider = Column(Enum('google', 'openai', 'anthropic', 'deepseek', name='provider_enum', native_enum=False))
    client = relationship("Client", back_populates="api_keys") 