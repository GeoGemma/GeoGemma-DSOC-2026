import logging
import traceback
from typing import Dict, Any, Callable, TypeVar, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AppError(Exception):
    """Base application error class."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

def handle_error(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for handling errors in API endpoints.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function that handles errors
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AppError as e:
            logger.error(f"Application error: {e.message}, status_code: {e.status_code}, details: {e.details}")
            raise HTTPException(status_code=e.status_code, detail={"message": e.message, "details": e.details})
        except HTTPException:
            # Re-raise HTTPException as is
            raise
        except Exception as e:
            logger.exception(f"Unhandled error in {func.__name__}: {str(e)}")
            raise HTTPException(status_code=500, detail={"message": "Internal Server Error", "details": str(e)})
    
    return wrapper

def format_error_response(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format a standardized error response.
    
    Args:
        message: The error message
        details: Additional error details
        
    Returns:
        Formatted error response
    """
    return {
        "success": False,
        "message": message,
        "data": details
    }

def log_exception(e: Exception, context: str = "") -> None:
    """
    Log an exception with context and stack trace.
    
    Args:
        e: The exception to log
        context: Additional context
    """
    if context:
        logger.error(f"Error in {context}: {str(e)}")
    else:
        logger.error(f"Error: {str(e)}")
    
    logger.error(traceback.format_exc()) 