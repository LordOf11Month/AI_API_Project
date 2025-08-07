"""
Chat Management Module

This module provides functions for managing chat sessions and messages in the
database. It handles the creation of new chats, retrieval of chat history, and
the addition of new messages to a conversation.

Key Functions:
- create_chat: Creates a new chat session for a client.
- chat_history: Retrieves the full message history for a given chat.
- add_message: Adds a new message to a chat with an auto-incrementing index.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select
from app.DB_connection.database import get_db
from app.models.DBModels import Chat, Message
from app.utils.console_logger import info, error, debug
from app.models.DataModels import message

async def create_chat(client_id: UUID) -> UUID:
    """
    Creates a new chat session for a given client.
    
    Args:
        client_id (UUID): The unique identifier of the client starting the chat.
        
    Returns:
        UUID: The unique identifier of the newly created chat session.
    """
    try:
        info(f"Creating new chat", "[ChatManager]")
        debug(f"chat for client_id: {client_id}", "[ChatManager]")
        async for db in get_db():
            new_chat = Chat(
                client_id=client_id
            )
            db.add(new_chat)
            await db.commit()
            await db.refresh(new_chat)
            debug(f"chat created with id: {new_chat.id}", "[ChatManager]")
            return new_chat.id 
    except Exception as e:
        error(f"Error creating chat: {e}", "[ChatManager]")
        raise
    
async def chat_history(chat_id:UUID | None) -> List[message]:
    """
    Retrieves the message history for a given chat session.
    
    Args:
        chat_id (UUID | None): The unique identifier of the chat.
        
    Returns:
        List[message]: A list of message objects representing the conversation history.
    """
    try:
        result = []
        if chat_id is None:
            return result
        async for db in get_db():
            messages_result = await db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.index))
            messages = messages_result.scalars().all()
        
            for msg in messages:
                result.append(message(role=msg.role, content=msg.content))
            return result
    except Exception as e:
        error(f"Error getting chat history: {e}", "[ChatManager]")
        raise
         

         
async def add_message(chat_id:UUID, message: message) -> Message:
    """
    Adds a new message to a chat session with an auto-incrementing index.
    
    Args:
        chat_id (UUID): The unique identifier of the chat.
        message (message): The message object to add to the chat.
        
    Returns:
        Message: The newly created message object from the database.
    """
    try:
        async for db in get_db():
            # Get the highest index for this chat
            last_message_result = await db.execute(
                select(Message.index)
                .where(Message.chat_id == chat_id)
                .order_by(Message.index.desc())
                .limit(1)
            )
            last_index = last_message_result.scalar_one_or_none()
            next_index = (last_index + 1) if last_index is not None else 0

            new_message = Message(
                chat_id=chat_id,
                role=message.role,
                content=message.content,
                index=next_index
            )
            db.add(new_message)
            await db.commit()
            await db.refresh(new_message)
            debug(f"message added to chat: {chat_id} with index: {next_index}", "[ChatManager]")
            return new_message
    except Exception as e:
        error(f"Error adding message: {e}", "[ChatManager]")
        raise
