# Standard library imports
from datetime import datetime

# Project imports
from app.models.DataModels import RequestLog, ResponseLog
from app.models.DBModels import Request
from app.database import SessionLocal

# Local dataclass definitions have been moved to app.models.DataModels

async def log_request(request: RequestLog):
    '''
    Logs a request to the database.
    '''
    db = SessionLocal()
    try:
        db_request = Request(
            chat_id=request.chat_id,
            request=request.user_prompt,
            model_name=request.model_name,
            # system_prompt_tenants will be updated later if needed
        )
        db.add(db_request)
        db.commit()
    finally:
        db.close()

async def log_response(response: ResponseLog):
    '''
    Logs a response to the database by updating the corresponding request.
    '''
    db = SessionLocal()
    try:
        # Since we don't have the request ID, we'll find the last request
        # for the given chat_id and assume it's the one to update.
        # This is not ideal, a more robust solution would be to pass the
        # request ID from log_request to log_response.
        db_request = db.query(Request).filter(Request.request_id == response.request_id).order_by(Request.created_at.desc()).first()
        if db_request:
            db_request.response = response.response
            db_request.input_tokens = response.input_tokens
            db_request.output_tokens = response.output_tokens
            db_request.status = response.status
            db_request.error_message = response.error_message
            db.commit()
    finally:
        db.close()