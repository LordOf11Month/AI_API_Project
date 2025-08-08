"""
Custom Console Logger

This module provides a simple, configurable console logger with color-coded
output for different log levels (INFO, WARNING, ERROR, DEBUG). The logger's
behavior can be controlled through environment variables.

Key Features:
- Four log levels: info, warning, error, debug
- Color-coded output for improved readability
- Enable/disable log levels and colors via environment variables or functions
- Optional prefixes for categorizing log messages (e.g., component name)

Environment Variables:
- LOG_INFO: 'true' or 'false' (default: 'true')
- LOG_WARNING: 'true' or 'false' (default: 'true')
- LOG_ERROR: 'true' or 'false' (default: 'true')
- LOG_DEBUG: 'true' or 'false' (default: 'false')
- LOG_COLOR: 'true' or 'false' (default: 'true')

Author: Ramazan Seçilmiş
Version: 1.0.0
"""
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# ANSI color codes
COLORS = {
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'BLUE': '\033[94m',
    'RESET': '\033[0m',
    'BOLD': '\033[1m'
}

# Configuration from environment variables
LOG_CONFIG = {
    'info_enabled': os.getenv('LOG_INFO', 'true').lower() == 'true',
    'warning_enabled': os.getenv('LOG_WARNING', 'true').lower() == 'true',
    'error_enabled': os.getenv('LOG_ERROR', 'true').lower() == 'true',
    'debug_enabled': os.getenv('LOG_DEBUG', 'false').lower() == 'true',
    'color_enabled': os.getenv('LOG_COLOR', 'true').lower() == 'true'
}

def _format_message(level: str, message: str, prefix: str = "") -> str:
    """
    Formats a log message with a colored level header and optional prefix.
    """
    color_map = {
        'INFO': COLORS['GREEN'],
        'WARNING': COLORS['YELLOW'],
        'ERROR': COLORS['RED'],
        'DEBUG': COLORS['BLUE']
    }
    
    if LOG_CONFIG['color_enabled']:
        color = color_map.get(level, '')
        reset = COLORS['RESET']
        bold = COLORS['BOLD']
        header = f"{color}{bold}[{level}]{reset}"
    else:
        header = f"[{level}]"
    
    if prefix:
        return f"{header} {prefix} {message}"
    else:
        return f"{header} {message}"

def info(message: str, prefix: str = "") -> None:
    """
    Logs an informational message (green).
    
    Used for general workflow and status updates.
    
    Args:
        message (str): The message to log.
        prefix (str, optional): A prefix for categorizing the message.
    """
    if LOG_CONFIG['info_enabled']:
        formatted_message = _format_message("INFO", message, prefix)
        print(formatted_message)

def warning(message: str, prefix: str = "") -> None:
    """
    Logs a warning message (yellow).
    
    Used for potential issues that don't stop the application.
    
    Args:
        message (str): The message to log.
        prefix (str, optional): A prefix for categorizing the message.
    """
    if LOG_CONFIG['warning_enabled']:
        formatted_message = _format_message("WARNING", message, prefix)
        print(formatted_message)

def error(message: str, prefix: str = "") -> None:
    """
    Logs an error message (red).
    
    Used for critical errors that may affect functionality.
    
    Args:
        message (str): The message to log.
        prefix (str, optional): A prefix for categorizing the message.
    """
    if LOG_CONFIG['error_enabled']:
        formatted_message = _format_message("ERROR", message, prefix)
        print(formatted_message)

def debug(message: str, prefix: str = "") -> None:
    """
    Logs a debug message (blue).
    
    Used for detailed information and variable values for debugging.
    
    Args:
        message (str): The message to log.
        prefix (str, optional): A prefix for categorizing the message.
    """
    if LOG_CONFIG['debug_enabled']:
        formatted_message = _format_message("DEBUG", message, prefix)
        print(formatted_message)

# Configuration utilities
def enable_log_level(level: str) -> None:
    """Enables a specific log level (e.g., 'info', 'debug')."""
    key = f"{level.lower()}_enabled"
    if key in LOG_CONFIG:
        LOG_CONFIG[key] = True

def disable_log_level(level: str) -> None:
    """Disables a specific log level."""
    key = f"{level.lower()}_enabled"
    if key in LOG_CONFIG:
        LOG_CONFIG[key] = False

def enable_colors() -> None:
    """Enables colored log output."""
    LOG_CONFIG['color_enabled'] = True

def disable_colors() -> None:
    """Disables colored log output."""
    LOG_CONFIG['color_enabled'] = False

def get_config() -> dict:
    """Returns the current logging configuration."""
    return LOG_CONFIG.copy()

def set_config(**kwargs) -> None:
    """
    Sets multiple logging configuration options at once.
    
    Args:
        **kwargs: Keyword arguments for configuration options (e.g.,
                  info_enabled=True, color_enabled=False).
    """
    for key, value in kwargs.items():
        if key in LOG_CONFIG:
            LOG_CONFIG[key] = bool(value)
