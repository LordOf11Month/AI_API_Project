"""
Password Utilities

This module provides utility functions for handling password hashing and
verification using the passlib library. It ensures that passwords are stored
securely and can be verified without storing them in plaintext.

Key Functions:
- verify_password: Verifies a plaintext password against a hashed one.
- get_password_hash: Hashes a plaintext password using bcrypt.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""
from passlib.context import CryptContext
from app.utils import console_logger

# Create a CryptContext instance, specifying the hashing schemes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a hashed password.
    
    Args:
        plain_password (str): The plaintext password to verify.
        hashed_password (str): The hashed password from the database.
        
    Returns:
        bool: True if the passwords match, False otherwise.
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
    Hashes a plaintext password using bcrypt.
    
    Args:
        password (str): The plaintext password to hash.
        
    Returns:
        str: The resulting hashed password.
    """
    console_logger.info("Hashing password", "[Password]")
    console_logger.debug("Starting password hashing process", "[Password]")
    
    hashed = pwd_context.hash(password)
    
    console_logger.info("Password hashed successfully", "[Password]")
    console_logger.debug(f"Password hash length: {len(hashed)}", "[Password]")
    
    return hashed 