import logging
import os
import asyncio
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Global variables for GenAI state
GENAI_INITIALIZED = False
GENAI_INITIALIZATION_ERROR = None
GENAI_CLIENT = None
GENAI_MODEL_NAME = None

async def initialize_genai() -> bool:
    """
    Initialize the GenAI client asynchronously.
    
    Returns:
        True if initialization succeeded, False otherwise
    """
    global GENAI_INITIALIZED, GENAI_INITIALIZATION_ERROR, GENAI_CLIENT, GENAI_MODEL_NAME
    
    try:
        # Get API key from environment
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            error_msg = "GEMINI_API_KEY not set in environment"
            logger.error(error_msg)
            GENAI_INITIALIZATION_ERROR = error_msg
            GENAI_INITIALIZED = False
            return False
        
        # Get model name from environment or use default
        model_name = os.environ.get("GEMINI_MODEL", "gemma-3-4b-it")
        
        # Run the actual initialization in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, lambda: _initialize_genai_sync(api_key, model_name)
        )
        
        return success
    except Exception as e:
        error_msg = f"Unexpected error during GenAI initialization: {str(e)}"
        logger.error(error_msg, exc_info=True)
        GENAI_INITIALIZATION_ERROR = error_msg
        GENAI_INITIALIZED = False
        return False

def _initialize_genai_sync(api_key: str, model_name: str) -> bool:
    """
    Synchronous GenAI initialization to be run in a thread pool.
    
    Args:
        api_key: The Google GenAI API key
        model_name: The model name to use
        
    Returns:
        True if initialization succeeded, False otherwise
    """
    global GENAI_INITIALIZED, GENAI_INITIALIZATION_ERROR, GENAI_CLIENT, GENAI_MODEL_NAME
    
    try:
        logger.info(f"Initializing Google GenAI client with model: {model_name}")
        
        # Initialize the client
        client = genai.Client(api_key=api_key)
        
        # Test the client with a simple request
        test_result = _test_genai_client(client, model_name)
        if not test_result:
            GENAI_INITIALIZED = False
            return False
        
        # Store the client and model name
        GENAI_CLIENT = client
        GENAI_MODEL_NAME = model_name
        GENAI_INITIALIZED = True
        GENAI_INITIALIZATION_ERROR = None
        
        logger.info(f"Google GenAI client initialized successfully with model: {model_name}")
        return True
    except Exception as e:
        error_msg = f"GenAI initialization failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        GENAI_INITIALIZATION_ERROR = error_msg
        GENAI_INITIALIZED = False
        return False

def _test_genai_client(client, model_name: str) -> bool:
    """
    Test the GenAI client with a simple request.
    
    Args:
        client: The GenAI client
        model_name: The model name to use
        
    Returns:
        True if the test succeeded, False otherwise
    """
    try:
        # Simple test prompt
        test_prompt = "Hello, world!"
        
        # Prepare content
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=test_prompt)],
            ),
        ]
        
        # Configure generation parameters
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        
        # Test generation
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=generate_content_config,
        )
        
        if response and hasattr(response, 'text'):
            logger.info("GenAI test successful")
            return True
        else:
            logger.error(f"GenAI test failed: response has no text attribute: {response}")
            GENAI_INITIALIZATION_ERROR = "GenAI test failed: invalid response from model"
            return False
    except Exception as e:
        logger.error(f"GenAI test failed: {str(e)}")
        GENAI_INITIALIZATION_ERROR = f"GenAI test failed: {str(e)}"
        return False

def get_genai_status() -> Dict[str, Any]:
    """
    Get the current status of GenAI.
    
    Returns:
        Dictionary with status information
    """
    return {
        "initialized": GENAI_INITIALIZED,
        "error": GENAI_INITIALIZATION_ERROR,
        "model": GENAI_MODEL_NAME if GENAI_INITIALIZED else None
    }

async def generate_text(prompt: str) -> Optional[str]:
    """
    Generate text using the GenAI client.
    
    Args:
        prompt: The prompt to generate text from
        
    Returns:
        The generated text or None if generation failed
    """
    if not GENAI_INITIALIZED or not GENAI_CLIENT:
        logger.error(f"GenAI not initialized: {GENAI_INITIALIZATION_ERROR}")
        return None
    
    try:
        # Run the generation in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: _generate_text_sync(prompt)
        )
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        return None

def _generate_text_sync(prompt: str) -> Optional[str]:
    """
    Synchronous text generation to be run in a thread pool.
    
    Args:
        prompt: The prompt to generate text from
        
    Returns:
        The generated text or None if generation failed
    """
    try:
        # Prepare content
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]
        
        # Configure generation parameters
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        
        # Accumulate text from streaming response
        response_text = ""
        for chunk in GENAI_CLIENT.models.generate_content_stream(
            model=GENAI_MODEL_NAME,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text or ""
        
        return response_text
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        return None 