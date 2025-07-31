from uuid import UUID
from sqlalchemy import select, delete, update
from app.DB_connection.database import get_db
from app.models.DBModels import APIKey
from app.utils.console_logger import info, error, debug
import os
from typing import Tuple

async def get_api_key(provider: str, client_id: str) -> Tuple[str, bool]:
    '''
    Returns a tuple of (api_key, is_client_api) for the given provider and client ID.
    If no API key is found in database, falls back to environment variable.
    is_client_api will be True if the key was found in the database, False if using environment variable.
    Raises ValueError if no API key is found in either location.
    '''
    try:
        info(f"Retrieving API key for provider: {provider}", "[APIManager]")
        debug(f"client_id: {client_id}", "[APIManager]")
        
        async for db in get_db():
            result = await db.execute(
                select(APIKey)
                .where(APIKey.provider == provider)
                .where(APIKey.client_id == client_id)
            )
            api_key = result.scalar()
            
            if api_key:
                debug(f"API key found in database for provider: {provider}", "[APIManager]")
                return str(api_key.api_key), True
            
            # If no API key in database, try environment variable
            env_key = os.getenv(f"{provider.upper()}_API_KEY")
            if env_key:
                debug(f"Using environment API key for provider: {provider}", "[APIManager]")
                return env_key, False
            
            # No API key found anywhere
            error(f"No API key found for provider {provider} in database or environment", "[APIManager]")
            raise ValueError(f"No API key found for provider {provider}")
                
    except ValueError as e:
        raise
    except Exception as e:
        error(f"Error retrieving API key: {e}", "[APIManager]")
        raise

async def store_api_key(provider: str, client_id: str, api_key: str):
    '''
    Stores the API key for the given provider and client ID.
    If an API key already exists for this provider and client, it will be updated.
    '''
    try:
        info(f"Storing API key for provider: {provider}", "[APIManager]")
        debug(f"client_id: {client_id}", "[APIManager]")
        
        async for db in get_db():
            # Check if an API key already exists
            existing_key = await db.execute(
                select(APIKey)
                .where(APIKey.provider == provider)
                .where(APIKey.client_id == client_id)
            )
            existing_key = existing_key.scalar()
            
            if existing_key:
                # Update existing key
                existing_key.api_key = UUID(api_key)
                debug(f"Updated existing API key for provider: {provider}", "[APIManager]")
            else:
                # Create new key
                new_key = APIKey(
                    api_key=UUID(api_key),
                    client_id=UUID(client_id),
                    provider=provider
                )
                db.add(new_key)
                debug(f"Created new API key for provider: {provider}", "[APIManager]")
            
            await db.commit()
            
    except ValueError as e:
        error(f"Invalid UUID format for API key or client ID: {e}", "[APIManager]")
        raise
    except Exception as e:
        error(f"Error storing API key: {e}", "[APIManager]")
        raise

async def delete_api_key(provider: str, client_id: str):
    '''
    Deletes the API key for the given provider and client ID.
    '''
    try:
        info(f"Deleting API key for provider: {provider}", "[APIManager]")
        debug(f"client_id: {client_id}", "[APIManager]")
        
        async for db in get_db():
            await db.execute(
                delete(APIKey)
                .where(APIKey.provider == provider)
                .where(APIKey.client_id == client_id)
            )
            await db.commit()
            
    except Exception as e:
        error(f"Error deleting API key: {e}", "[APIManager]")
        raise

async def update_api_key(provider: str, client_id: str, api_key: str):
    '''
    Updates the API key for the given provider and client ID.
    '''
    try:
        info(f"Updating API key for provider: {provider}", "[APIManager]")
        debug(f"client_id: {client_id}", "[APIManager]")    

        async for db in get_db():
            await db.execute(
                update(APIKey)
                .where(APIKey.provider == provider)
                .where(APIKey.client_id == client_id)   
                .values(api_key=UUID(api_key))
            )
            await db.commit()
            
    except Exception as e:
        error(f"Error updating API key: {e}", "[APIManager]")