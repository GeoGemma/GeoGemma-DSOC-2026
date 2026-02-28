import ee
import logging
import os
import time
import asyncio
from typing import Tuple, Optional, Dict, Any
from asyncio import Semaphore

logger = logging.getLogger(__name__)

# Earth Engine concurrency control
# Limit to a reasonable number of concurrent EE operations
# This helps prevent "Computation timed out" errors
EE_SEMAPHORE = Semaphore(5)  # Allow max 5 concurrent EE operations

# Global variables for Earth Engine state
EE_INITIALIZED = False
EE_INITIALIZATION_ERROR = None

async def initialize_earth_engine(project_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Initialize Earth Engine asynchronously with the given project ID.
    
    Args:
        project_id: The Google Cloud project ID for Earth Engine
        
    Returns:
        Tuple of (success, error_message)
    """
    global EE_INITIALIZED, EE_INITIALIZATION_ERROR
    
    if not project_id:
        error_msg = "Project ID was not provided to initialize Earth Engine."
        logger.error(error_msg)
        EE_INITIALIZED = False
        EE_INITIALIZATION_ERROR = error_msg
        return False, error_msg
    
    # Run the actual authentication in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    try:
        success, error = await loop.run_in_executor(
            None, lambda: _initialize_ee_sync(project_id)
        )
        EE_INITIALIZED = success
        EE_INITIALIZATION_ERROR = error
        return success, error
    except Exception as e:
        error_msg = f"Unexpected error during Earth Engine initialization: {str(e)}"
        logger.error(error_msg, exc_info=True)
        EE_INITIALIZED = False
        EE_INITIALIZATION_ERROR = error_msg
        return False, error_msg

def _initialize_ee_sync(project_id: str) -> Tuple[bool, Optional[str]]:
    """
    Synchronous Earth Engine initialization to be run in a thread pool.
    
    Args:
        project_id: The Google Cloud project ID for Earth Engine
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        logger.info(f"Attempting Earth Engine authentication with project ID: {project_id}")
        
        # Try to initialize Earth Engine with service account credentials
        try:
            # First try with service account credentials
            credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path and os.path.exists(credentials_path):
                logger.info(f"Using service account credentials from {credentials_path}")
                credentials = ee.ServiceAccountCredentials(None, credentials_path)
                ee.Initialize(credentials, project=project_id)
                logger.info(f"Earth Engine initialized successfully with project: {project_id} using service account")
                return True, None
            else:
                # Fall back to application default credentials
                logger.info("Service account credentials not found, using application default credentials")
                ee.Initialize(project=project_id)
                logger.info(f"Earth Engine initialized successfully with project: {project_id} using app default credentials")
                return True, None
        except Exception as e:
            # If service account fails, try with application default 
            logger.warning(f"Service account initialization failed: {e}, trying app default")
            try:
                ee.Initialize(project=project_id)
                logger.info(f"Earth Engine initialized successfully with project: {project_id} using app default credentials")
                return True, None
            except Exception as inner_e:
                # If both methods fail, raise the error
                raise inner_e

    except Exception as e:
        # Catch potential errors like google.auth.exceptions.DefaultCredentialsError
        error_msg = f"Earth Engine initialization failed (Unexpected Error): {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

def get_ee_status() -> Dict[str, Any]:
    """
    Get the current status of Earth Engine.
    
    Returns:
        Dictionary with status information
    """
    return {
        "initialized": EE_INITIALIZED,
        "error": EE_INITIALIZATION_ERROR
    }

async def run_ee_operation(operation_func, *args, **kwargs):
    """
    Run an Earth Engine operation with concurrency control.
    
    Args:
        operation_func: The function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the operation
    """
    if not EE_INITIALIZED:
        raise RuntimeError(f"Earth Engine not initialized: {EE_INITIALIZATION_ERROR}")
    
    # Use the semaphore to limit concurrent operations
    async with EE_SEMAPHORE:
        # Run the operation in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            start_time = time.time()
            result = await loop.run_in_executor(
                None, lambda: operation_func(*args, **kwargs)
            )
            duration = time.time() - start_time
            logger.debug(f"Earth Engine operation completed in {duration:.2f} seconds")
            return result
        except Exception as e:
            logger.error(f"Error in Earth Engine operation: {e}")
            raise