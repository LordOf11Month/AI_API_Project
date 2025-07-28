from typing import Dict
from uuid import UUID
import uuid
from app.DB_connection.database import get_db
from sqlalchemy import select
from app.models.DBModels import Request,Chat


async def chat_complier(chat_id:UUID, messages:list[Dict[str, str]], provider:str,userprompt:str):
    '''this method takes empty messages dic and chat id and if uuid is none/null it create new chat in chat table and assign chat_id uuid to uuid of this new chat if chat_id has value it searchs database for requests with same id. then it will put them in message dict in correct order and return'''
    async for db in get_db():
        if chat_id is None:
            new_chat = Chat()
            db.add(new_chat)
            await db.commit()
            chat_id = new_chat.id
        else:
            requests_result = await db.execute(select(Request).where(Request.chat_id == chat_id).order_by(Request.created_at))
            requests = requests_result.scalars().all()
            

            # for bad guys who doesnt follow regular naming 
            provider_map = {
                'google': 'parts',
            }
            content_field = provider_map.get(provider, 'content')


            for req in requests:
                messages.append({'role':'user',content_field: req.request})
                messages.append({'role':'assistant', content_field: req.response})
            messages.append({"role": "user", content_field: userprompt})
            
    
    return chat_id, messages 