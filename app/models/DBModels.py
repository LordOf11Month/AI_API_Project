from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, BOOLEAN, TEXT, SMALLINT, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import  relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Provider(Enum):
    GOOGLE = 'google'
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    DEEPSEEK = 'deepseek'

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
    prompt_template_name = Column(String(255), ForeignKey('prompt_templates.name'))
    model_name = Column(TEXT, )
    request = Column(TEXT)
    response = Column(TEXT)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    status = Column(BOOLEAN)
    error_message = Column(TEXT, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_client_api = Column(BOOLEAN, default=False)
    provider = Column(Enum(Provider, name='provider_enum', native_enum=False))
    chat = relationship("Chat", back_populates="requests")
    client = relationship("Client")
    prompt_template = relationship("PromptTemplate")

    __table_args__ = (
        Index('idx_requests_chat_id', 'chat_id'),
        Index('idx_requests_created_at', 'created_at'),
    )

class APIKey(Base):
    __tablename__ = 'api_keys'
    api_key = Column(UUID(as_uuid=True), primary_key=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    provider = Column(Enum(Provider, name='provider_enum', native_enum=False))
    client = relationship("Client", back_populates="api_keys") 