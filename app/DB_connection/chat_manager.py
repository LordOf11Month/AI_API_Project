from typing import Dict
from uuid import UUID

from sqlalchemy import select
from app.DB_connection.database import get_db
from app.models.DBModels import Chat, Request
from datetime import datetime


async def create_chat(client_id: str) -> UUID:
    """
    Creates a new chat entry in the database.
    Returns the UUID of the newly created chat.
    """
    async for db in get_db():
        new_chat = Chat(
            client_id=client_id,
            created_at=datetime.now()
        )
        db.add(new_chat)
        await db.commit()
        await db.refresh(new_chat)
        return new_chat.id 
    
async def chat_history(chat_id:UUID | None) -> list[Dict[str, str]]:
    '''
    Returns the history of a chat.
    '''
    messages = []
    if chat_id is None:
        return messages
    async for db in get_db():
        requests_result = await db.execute(select(Request).where(Request.chat_id == chat_id).order_by(Request.created_at))
        requests = requests_result.scalars().all()
    
        for req in requests:
            messages.append({'request':req.request,"response": req.response})
    return messages
         
