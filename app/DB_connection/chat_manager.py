from typing import Dict
from uuid import UUID

from sqlalchemy import select
from app.DB_connection.database import get_db
from app.models.DBModels import Chat, Request
from datetime import datetime, timezone
from app.utils.console_logger import info, error, debug


async def create_chat(client_id: UUID) -> UUID:
    """
    Creates a new chat session for a given client.
    """
    try:
        info(f"Creating new chat", "[ChatManager]")
        debug(f"chat for client_id: {client_id}", "[ChatManager]")
        async for db in get_db():
            new_chat = Chat(
                client_id=client_id,
                created_at=datetime.now(timezone.utc)
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
        messages = []
        if chat_id is None:
            return messages
        async for db in get_db():
            requests_result = await db.execute(select(Request).where(Request.chat_id == chat_id).order_by(Request.created_at))
            requests = requests_result.scalars().all()
        
            for req in requests:
                    messages.append({'request':req.request,"response": req.response})
            return messages
    except Exception as e:
        error(f"Error getting chat history: {e}", "[ChatManager]")
        raise
         
