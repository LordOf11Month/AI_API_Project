"""
API Key Management Module

This module provides functions for managing client-specific API keys in the
database. It handles retrieving, storing, updating, and deleting API keys for
different AI providers, with a fallback to system-wide environment variables.

Key Functions:
- get_api_key: Retrieves a client's API key, falling back to an environment
  variable if not found in the database.
- store_api_key: Stores or updates an API key for a client.
- delete_api_key: Removes a client's API key from the database.
- update_api_key: Updates an existing API key for a client.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""

from uuid import UUID
from sqlalchemy import select, delete, update
from app.DB_connection.database import get_db
from app.models.DBModels import APIKey
from app.models.DataModels import Response
from app.utils.console_logger import info, error, debug
import os
from typing import Tuple

async def get_api_key(provider: str, client_id: str) -> Tuple[str, bool]:
    """
    Retrieves an API key for a given provider and client.
    
    This function first checks the database for a client-specific key. If not
    found, it falls back to the system-wide environment variable for that provider.
    
    Args:
        provider (str): The AI provider (e.g., 'openai', 'google').
        client_id (str): The unique identifier of the client.
        
    Returns:
        Tuple[str, bool]: A tuple containing the API key and a boolean indicating
                          if the key is client-specific (True) or from an
                          environment variable (False).
                          
    Raises:
        ValueError: If no API key is found in either the database or environment.
    """
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
    """
    Stores or updates a client-specific API key in the database.
    
    If a key already exists for the client and provider, it will be updated.
    Otherwise, a new key will be created.
    
    Args:
        provider (str): The AI provider.
        client_id (str): The client's unique identifier.
        api_key (str): The API key to store.
    """
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
    """
    Deletes a client-specific API key from the database.
    
    Args:
        provider (str): The AI provider.
        client_id (str): The client's unique identifier.
    """
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
    """
    Updates an existing client-specific API key in the database.
    
    Args:
        provider (str): The AI provider.
        client_id (str): The client's unique identifier.
        api_key (str): The new API key to set.
    """
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
        return Response(type="error", error=str(e))