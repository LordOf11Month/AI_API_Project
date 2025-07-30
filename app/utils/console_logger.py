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
    """Format message with color and prefix."""
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
    Log info messages - shows workflow of service (GREEN header).
    These logs run nearly always and show the normal workflow.
    
    Args:
        message: The message to log
        prefix: Optional prefix for the log message (e.g., "[Database]")
    """
    if LOG_CONFIG['info_enabled']:
        formatted_message = _format_message("INFO", message, prefix)
        print(formatted_message)

def warning(message: str, prefix: str = "") -> None:
    """
    Log warning messages - shows problems that might cause issues (YELLOW header).
    System works most of the time but there are potential problems.
    
    Args:
        message: The message to log
        prefix: Optional prefix for the log message (e.g., "[Database]")
    """
    if LOG_CONFIG['warning_enabled']:
        formatted_message = _format_message("WARNING", message, prefix)
        print(formatted_message)

def error(message: str, prefix: str = "") -> None:
    """
    Log error messages - shows critical errors (RED header).
    These cause unfunctionality and might stop the program.
    
    Args:
        message: The message to log
        prefix: Optional prefix for the log message (e.g., "[Database]")
    """
    if LOG_CONFIG['error_enabled']:
        formatted_message = _format_message("ERROR", message, prefix)
        print(formatted_message)

def debug(message: str, prefix: str = "") -> None:
    """
    Log debug messages - shows detailed workflow with variable values (BLUE header).
    Provides detailed information for debugging purposes.
    
    Args:
        message: The message to log
        prefix: Optional prefix for the log message (e.g., "[Database]")
    """
    if LOG_CONFIG['debug_enabled']:
        formatted_message = _format_message("DEBUG", message, prefix)
        print(formatted_message)

# Configuration utilities
def enable_log_level(level: str) -> None:
    """Enable a specific log level."""
    key = f"{level.lower()}_enabled"
    if key in LOG_CONFIG:
        LOG_CONFIG[key] = True

def disable_log_level(level: str) -> None:
    """Disable a specific log level."""
    key = f"{level.lower()}_enabled"
    if key in LOG_CONFIG:
        LOG_CONFIG[key] = False

def enable_colors() -> None:
    """Enable colored output."""
    LOG_CONFIG['color_enabled'] = True

def disable_colors() -> None:
    """Disable colored output."""
    LOG_CONFIG['color_enabled'] = False

def get_config() -> dict:
    """Get current logging configuration."""
    return LOG_CONFIG.copy()

def set_config(**kwargs) -> None:
    """
    Set logging configuration.
    
    Args:
        info_enabled: Enable/disable info logs
        warning_enabled: Enable/disable warning logs
        error_enabled: Enable/disable error logs
        debug_enabled: Enable/disable debug logs
        color_enabled: Enable/disable colored output
    """
    for key, value in kwargs.items():
        if key in LOG_CONFIG:
            LOG_CONFIG[key] = bool(value)

# Backward compatibility
def debug_log(message: str, prefix: str = "") -> None:
    """Backward compatibility for existing debug_log function."""
    debug(message, prefix) 