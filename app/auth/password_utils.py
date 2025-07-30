from passlib.context import CryptContext
from app.utils import console_logger

# Create a CryptContext instance, specifying the hashing schemes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed one.
    """
    console_logger.info("Verifying password", "[Password]")
    console_logger.debug("Starting password verification process", "[Password]")
    
    result = pwd_context.verify(plain_password, hashed_password)
    
    if result:
        console_logger.info("Password verification successful", "[Password]")
    else:
        console_logger.warning("Password verification failed", "[Password]")
    
    return result

def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.
    """
    console_logger.info("Hashing password", "[Password]")
    console_logger.debug("Starting password hashing process", "[Password]")
    
    hashed = pwd_context.hash(password)
    
    console_logger.info("Password hashed successfully", "[Password]")
    console_logger.debug(f"Password hash length: {len(hashed)}", "[Password]")
    
    return hashed 