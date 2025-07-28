# Standard library imports
from datetime import datetime

# Project imports
from app.models.DataModels import RequestLog, ResponseLog, SystemPrompt
from app.models.DBModels import Request, Chat, PromptTemplate
from .database import get_db
from sqlalchemy import select

# Local dataclass definitions have been moved to app.models.DataModels

async def initialize_request(request: RequestLog):
    '''
    Initializes a new request record in the database.
    Returns the request ID for later finalization.
    '''
    async for db in get_db():
        try:
            # Get client_id from the chat
            result = await db.execute(select(Chat).where(Chat.id == request.chat_id))
            chat = result.scalars().first()
            if not chat:
                raise ValueError(f"Chat with ID {request.chat_id} not found")

            
            if request.system_prompt and isinstance(request.system_prompt, SystemPrompt):
                template_name = request.system_prompt.template
                template_result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == template_name))
                prompt_template = template_result.scalars().first()
                
                if not prompt_template:
                    raise ValueError(f"PromptTemplate with name '{template_name}' not found")

                prompt_template_id = prompt_template.id
                template_version = prompt_template.version
                system_prompt_tenants = request.system_prompt.tenants
                
            # Create the request record
            db_request = Request(
                chat_id=request.chat_id,
                client_id=request.client_id,  # Get client_id from the chat
                prompt_template_id=prompt_template_id,
                system_prompt_tenants=system_prompt_tenants,
                template_version=template_version,
                model_name=request.model_name,
                request=request.user_prompt,
                response="",  # Will be updated by finalize_request
                status=None,  # Will be updated by finalize_request
                created_at=request.created_at
            )
            
            db.add(db_request)
            await db.commit()
            return db_request.id  # Return the ID so it can be used in finalize_request
            
        except Exception as e:
            await db.rollback()
            print(f"Error initializing request: {e}")
            raise e

async def finalize_request(response: ResponseLog):
    '''
    Finalizes a request by updating it with the response data.
    '''
    async for db in get_db():
        try:
            result = await db.execute(select(Request).where(Request.id == response.request_id))
            db_request = result.scalars().first()
            
            if db_request:
                db_request.response = response.response
                db_request.input_tokens = response.input_tokens
                db_request.output_tokens = response.output_tokens
                db_request.status = response.status
                db_request.error_message = response.error_message
                await db.commit()
            else:
                print(f"Warning: No request found with ID {response.request_id} to finalize.")
        except Exception as e:
            await db.rollback()
            print(f"Error finalizing request: {e}")
            raise e