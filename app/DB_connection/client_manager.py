from datetime import datetime, timezone
from sqlalchemy.future import select
from app.DB_connection.database import get_db
from app.models.DBModels import Client
from app.auth.password_utils import get_password_hash, verify_password
from app.models.DataModels import ClientCredentials


async def create_client(credentials: ClientCredentials) -> Client:
    """
    Creates a new client in the database with a hashed password.
    """
    async for db in get_db():
        hashed_password = get_password_hash(credentials.password)
        new_client = Client(email=credentials.email, password=hashed_password, created_at=datetime.now(timezone.utc))
        db.add(new_client)
        await db.commit()
        await db.refresh(new_client)
        return new_client


async def authenticate_client(credentials: ClientCredentials) -> Client | None:
    """
    Authenticates a client by email and password.
    Returns the client object if authentication is successful, otherwise None.
    """
    async for db in get_db():
        result = await db.execute(select(Client).where(Client.email == credentials.email))
        client = result.scalars().first()
        if client and verify_password(credentials.password, client.password):
            return client
        return None 