from typing import Dict
from uuid import UUID

from sqlalchemy import select
from app.DB_connection.database import get_db
from app.models.DBModels import Chat, Message
from app.utils.console_logger import info, error, debug
from app.models.DataModels import message

async def create_chat(client_id: UUID) -> UUID:
    """
    Creates a new chat session for a given client.
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
    
async def chat_history(chat_id:UUID | None) -> list[Dict[str, str]]:
    '''
    Returns the history of a chat.
    '''
    try:
        result = []
        if chat_id is None:
            return result
        async for db in get_db():
            messages_result = await db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.index))
            messages = messages_result.scalars().all()
        
            for msg in messages:
                result.append({'role':msg.role,"content": msg.content})
            return result
    except Exception as e:
        error(f"Error getting chat history: {e}", "[ChatManager]")
        raise
         

         
async def add_message(chat_id:UUID, message: message):
    '''
    Adds a message to the chat with an auto-incrementing index per chat.
    '''
    try:
        async for db in get_db():
            # Get the highest index for this chat
            last_message = await db.execute(
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.index.desc())
                .limit(1)
            )
            last_message = last_message.scalar()
            next_index = (last_message.index + 1) if last_message else 0

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
