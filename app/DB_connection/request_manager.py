"""
Request Management Module

This module provides functions for tracking AI generation requests in the database.
It handles the two main stages of a request's lifecycle: initialization and
finalization, ensuring that all relevant data is logged for analytics and
billing purposes.

Key Functions:
- initialize_request: Creates a new request record at the start of a request.
- finalize_request: Updates the request record with completion details,
  including token counts, status, and latency.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""
# Standard library imports
from sqlalchemy import select


# Project imports
from app.models.DataModels import RequestInit, RequestFinal
from app.models.DBModels import Request
from .database import get_db
from app.utils.console_logger import debug, info, warning, error

# Local dataclass definitions have been moved to app.models.DataModels


async def initialize_request(request: RequestInit):
    """
    Initializes a new request record in the database.
    
    This function should be called at the beginning of an AI generation request
    to create a preliminary record in the database.
    
    Args:
        request (RequestInit): An object containing the initial request data.
        
    Returns:
        UUID: The unique identifier of the newly created request record.
    """
    async for db in get_db():
        try:
            debug(f"Initializing request for client: {request.client_id}", "[RequestManager]")
            # Create the request record
            db_request = Request(
                client_id=request.client_id,  # Always log client_id for basic tracking
                model_name=request.model_name,  # None if advanced logging is disabled
                status=None,  # Will be updated by finalize_request
                model_provider=request.provider.value,
                is_client_api=request.is_client_api
            )
            
            db.add(db_request)
            await db.commit()
            await db.refresh(db_request)
            info(f"Request initialized with ID: {db_request.id}", "[RequestManager]")
            return db_request.id  # Return the ID so it can be used in finalize_request

        except Exception as e:
            await db.rollback()
            error(f"Error initializing request at line {e.__traceback__.tb_lineno}: {e}", "[RequestManager]")
            raise e

async def finalize_request(response: RequestFinal):
    """
    Finalizes a request record with completion details.
    
    This function is called after an AI generation request is complete to update
    the corresponding record with token counts, status, latency, and any errors.
    
    Args:
        response (RequestFinal): An object containing the final request data.
    """
    async for db in get_db():
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
                info(f"Request {response.request_id} finalized successfully", "[RequestManager]")
            else:
                warning(f"No request found with ID {response.request_id} to finalize", "[RequestManager]")
        except Exception as e:
            await db.rollback()
            error(f"Error finalizing request at line {e.__traceback__.tb_lineno}: {e}", "[RequestManager]")
            raise e