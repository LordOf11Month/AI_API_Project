from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get debug mode from environment variable, default to False
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

def debug_log(message: str, prefix: str = "") -> None:
    """
    Log debug messages if DEBUG_MODE is enabled.
    Args:
        message: The message to log
        prefix: Optional prefix for the log message (e.g., "[Dispatcher]")
    """
    if DEBUG_MODE:
        if prefix:
            print(f"{prefix} {message}")
        else:
            print(message) 