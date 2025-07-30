# Standard library imports
from datetime import datetime
import os

# Project imports
from app.models.DataModels import RequestLog, ResponseLog, SystemPrompt
from app.models.DBModels import Request, Chat, PromptTemplate
from .database import SessionLocal
from sqlalchemy import select
from app.utils import console_logger

# Local dataclass definitions have been moved to app.models.DataModels

# Check if advanced logging is enabled
def is_advanced_logging_enabled() -> bool:
    """Check if advanced logging is enabled from environment variable."""
    return os.getenv('ADVENCE_LOGING_ENABLED', 'false').lower() == 'true'

async def initialize_request(request: RequestLog):
    '''
    Initializes a new request record in the database.
    Returns the request ID for later finalization.
    '''
    async with SessionLocal() as db:
        try:
            is_advanced = is_advanced_logging_enabled()
            console_logger.info(f"Initializing request with advanced logging: {is_advanced}", "[RequestManager]")
            
            # Initialize variables for conditional logging
            chat_id = None
            template_name = None
            model_name = None
            user_prompt = None
            
            # Only process chat_id if advanced logging is enabled
            if is_advanced and request.chat_id:
                chat_id = request.chat_id
                result = await db.execute(select(Chat).where(Chat.id == request.chat_id))
                chat = result.scalars().first()
                if not chat:
                    console_logger.error(f"Chat with ID {request.chat_id} not found", "[RequestManager]")
                    raise ValueError(f"Chat with ID {request.chat_id} not found")
                console_logger.debug(f"Chat ID {chat_id} processed for logging", "[RequestManager]")

            
            # Only include sensitive data if advanced logging is enabled
            if is_advanced:
                model_name = request.model_name
                user_prompt = request.user_prompt
                template_name = request.system_prompt.template_name
                console_logger.debug("Including sensitive data in request log", "[RequestManager]")
            else:
                console_logger.info("Excluding sensitive data from request log (advanced logging disabled)", "[RequestManager]")
            
            # Create the request record
            db_request = Request(
                chat_id=chat_id,  # None if advanced logging is disabled
                client_id=request.client_id,  # Always log client_id for basic tracking
                prompt_template_name=template_name,  # None if advanced logging is disabled
                model_name=model_name,  # None if advanced logging is disabled
                request=user_prompt,  # None if advanced logging is disabled
                response=None,  # Will be updated by finalize_request
                status=None,  # Will be updated by finalize_request
                created_at=request.created_at,
                provider=request.provider,
                is_client_api=request.is_client_api
            )
            
            db.add(db_request)
            await db.commit()
            await db.refresh(db_request)
            console_logger.info(f"Request initialized with ID: {db_request.id}", "[RequestManager]")
            return db_request.id  # Return the ID so it can be used in finalize_request
            
        except Exception as e:
            await db.rollback()
            console_logger.error(f"Error initializing request: {e}", "[RequestManager]")
            raise e

async def finalize_request(response: ResponseLog):
    '''
    Finalizes a request by updating it with the response data.
    '''
    async with SessionLocal() as db:
        try:
            is_advanced = is_advanced_logging_enabled()
            console_logger.info(f"Finalizing request with advanced logging: {is_advanced}", "[RequestManager]")
            
            result = await db.execute(select(Request).where(Request.id == response.request_id))
            db_request = result.scalars().first()
            
            if db_request:
                # Only update response content if advanced logging is enabled
                if is_advanced:
                    db_request.response = response.response
                    console_logger.debug("Including response content in finalization", "[RequestManager]")
                else:
                    db_request.response = None
                    console_logger.info("Excluding response content from finalization (advanced logging disabled)", "[RequestManager]")
                
                # Always log token counts and status for basic metrics
                db_request.input_tokens = response.input_tokens
                db_request.output_tokens = response.output_tokens
                db_request.status = response.status
                db_request.error_message = response.error_message
                
                await db.commit()
                console_logger.info(f"Request {response.request_id} finalized successfully", "[RequestManager]")
            else:
                console_logger.warning(f"No request found with ID {response.request_id} to finalize", "[RequestManager]")
        except Exception as e:
            await db.rollback()
            console_logger.error(f"Error finalizing request: {e}", "[RequestManager]")
            raise e