# Standard library imports
from sqlalchemy import select


# Project imports
from app.models.DataModels import RequestInit, RequestFinal
from app.models.DBModels import Request
from .database import SessionLocal
from app.utils import console_logger, debug

# Local dataclass definitions have been moved to app.models.DataModels


async def initialize_request(request: RequestInit):
    '''
    Initializes a new request record in the database.
    Returns the request ID for later finalization.
    '''
    async with SessionLocal() as db:
        try:
            debug(f"Initializing request with ID: {request.request_id}", "[RequestManager]")
            # Create the request record
            db_request = Request(
                client_id=request.client_id,  # Always log client_id for basic tracking
                model_name=request.model_name,  # None if advanced logging is disabled
                status=None,  # Will be updated by finalize_request
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

async def finalize_request(response: RequestFinal):
    '''
    Finalizes a request by updating it with the response data.
    '''
    async with SessionLocal() as db:
        try:
            debug(f"Finalizing request with ID: {response.request_id}", "[RequestManager]")
            result = await db.execute(select(Request).where(Request.id == response.request_id))
            db_request = result.scalars().first()
            
            if db_request:
                # Always log token counts and status for basic metrics
                db_request.input_tokens = response.input_tokens
                db_request.output_tokens = response.output_tokens
                db_request.reasoning_tokens = response.reasoning_tokens
                db_request.status = response.status
                db_request.error_message = response.error_message
                db_request.latency = response.latency
                await db.commit()
                console_logger.info(f"Request {response.request_id} finalized successfully", "[RequestManager]")
            else:
                console_logger.warning(f"No request found with ID {response.request_id} to finalize", "[RequestManager]")
        except Exception as e:
            await db.rollback()
            console_logger.error(f"Error finalizing request: {e}", "[RequestManager]")
            raise e