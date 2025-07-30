from datetime import datetime, timezone
from sqlalchemy.future import select
from app.DB_connection.database import get_db
from app.models.DBModels import Client
from app.auth.password_utils import get_password_hash, verify_password
from app.models.DataModels import ClientCredentials
from app.utils.console_logger import info, warning, error, debug


async def create_client(credentials: ClientCredentials) -> Client:
    """
    Creates a new client in the database with a hashed password.
    """
    try:
        info(f"Attempting to create client with email: {credentials.email}", "[ClientManager]")
        async for db in get_db():
            hashed_password = get_password_hash(credentials.password)
            new_client = Client(email=credentials.email, password=hashed_password, created_at=datetime.now(timezone.utc))
            db.add(new_client)
            await db.commit()
            await db.refresh(new_client)
            info(f"Client created successfully with ID: {new_client.id}", "[ClientManager]")
            return new_client
    except Exception as e:
        error(f"Error creating client: {e}", "[ClientManager]")
        raise


async def authenticate_client(credentials: ClientCredentials) -> Client | None:
    """
    Authenticates a client by email and password.
    Returns the client object if authentication is successful, otherwise None.
    """
    try:
        info(f"Attempting to authenticate client with email: {credentials.email}", "[ClientManager]")
        async for db in get_db():
            result = await db.execute(select(Client).where(Client.email == credentials.email))
            client = result.scalars().first()
        if client and verify_password(credentials.password, client.password):
            info(f"Client authenticated successfully: {client.id}", "[ClientManager]")
            return client
        
        warning(f"Failed authentication attempt for email: {credentials.email}", "[ClientManager]")
        return None 
    except Exception as e:
        error(f"Error authenticating client: {e}", "[ClientManager]")
        raise
