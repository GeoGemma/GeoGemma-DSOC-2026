"""
Gemini client module for the GIS AI Agent.

This module provides a client for interacting with Google's Gemini API,
allowing the agent to use Gemini's language capabilities.
"""

import os
import logging
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Union
import asyncio

from ..config import get_config

# Configure logging
logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google's Gemini API."""

    def __init__(self):
        """Initialize the Gemini client."""
        self.config = get_config()
        self._setup_api()
        self.model_name = self.config.get_model_config().get("model_name", "gemini-2.0-flash")
        self.model = None
        self._initialize_model()

    def _setup_api(self) -> None:
        """Setup the Gemini API with API key."""
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("Gemini API key not found. Please set it in the configuration or environment variable.")
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
    
    def _get_api_key(self) -> Optional[str]:
        """Get the Gemini API key from configuration or environment."""
        # Try to get from configuration
        gemini_config = self.config.get_api_keys().get("gemini", {})
        api_key = gemini_config.get("api_key")
        
        # If not in configuration, try environment variable
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY")
        
        return api_key

    def _initialize_model(self) -> None:
        """Initialize the Gemini model."""
        try:
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Initialized Gemini model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise

    async def generate_text(self, 
                     prompt: str, 
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None,
                     tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate text using the Gemini model.

        Args:
            prompt: The prompt to send to the model.
            temperature: Temperature for sampling. Higher values make output more random.
            max_tokens: Maximum number of tokens to generate.
            tools: List of tools to make available to the model.

        Returns:
            Generated response from the model.
        """
        if not self.model:
            self._initialize_model()
        
        # Get default values from configuration if not provided
        model_config = self.config.get_model_config()
        if temperature is None:
            temperature = model_config.get("temperature", 0.7)
        if max_tokens is None:
            max_tokens = model_config.get("max_tokens", 4096)
        
        # Create generation config
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            top_p=model_config.get("top_p", 0.95),
            top_k=model_config.get("top_k", 40),
            max_output_tokens=max_tokens,
        )
        
        try:
            # Generate text
            if tools:
                logger.info(f"Calling Gemini with {len(tools)} tools")
                formatted_tools = tools
                # Debug tool format (Optional: remove if too verbose)
                # for tool in formatted_tools:
                #     if 'function_declarations' in tool:
                #         logger.debug(f"Tool declaration: {tool['function_declarations'][0]['name']}")
                
                logger.debug(f"Sending prompt to Gemini: {prompt[:100]}...") # Log start of prompt
                start_time = asyncio.get_event_loop().time()
                
                response = await self.model.generate_content_async(
                    prompt, 
                    generation_config=generation_config,
                    tools=formatted_tools,
                    request_options={"timeout": model_config.get("timeout", 60)} # Apply timeout
                )
                
                end_time = asyncio.get_event_loop().time()
                logger.info(f"Gemini API call completed in {end_time - start_time:.2f} seconds.")
                logger.debug(f"Raw Gemini response received: {response}") # Log raw response

            else:
                # Standard text generation without tools
                logger.debug(f"Sending prompt to Gemini (no tools): {prompt[:100]}...")
                start_time = asyncio.get_event_loop().time()
                
                response = await self.model.generate_content_async(
                    prompt, 
                    generation_config=generation_config,
                    request_options={"timeout": model_config.get("timeout", 60)} # Apply timeout
                )
                
                end_time = asyncio.get_event_loop().time()
                logger.info(f"Gemini API call (no tools) completed in {end_time - start_time:.2f} seconds.")
                logger.debug(f"Raw Gemini response received (no tools): {response}") # Log raw response
                
            # Process the response *after* logging raw
            processed_response = self._process_response(response)
            logger.debug(f"Processed response: {processed_response}")
            return processed_response
            
        except asyncio.TimeoutError:
            # Get timeout value before using in f-string
            timeout_duration = model_config.get("timeout", 60)
            logger.error(f"Gemini API call timed out after {timeout_duration} seconds.")
            raise TimeoutError("The request to the AI model timed out.")
        except Exception as e:
            # Log the specific type of exception
            logger.error(f"Error during Gemini API call ({type(e).__name__}): {e}")
            # Optionally re-raise or handle specific exceptions differently
            raise

    def _process_response(self, response: Any) -> Dict[str, Any]:
        """
        Process the response from the Gemini API.

        Args:
            response: The raw response from the Gemini API.

        Returns:
            Processed response with text and tool calls (if any).
        """
        # Log start of processing
        logger.debug("Starting to process Gemini response...")
        result = {
            "text": "",
            "tool_calls": []
        }
        
        try:
            # Process candidates and parts
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for part in candidate.content.parts:
                                # Check if it's a text part
                                if hasattr(part, 'text') and part.text:
                                    result["text"] += part.text  # Append text parts
                                
                                # Check if it's a function call part
                                elif hasattr(part, 'function_call'):
                                    try:
                                        name = getattr(part.function_call, 'name', None)
                                        args = {}
                                        if hasattr(part.function_call, 'args'):
                                            # The 'args' attribute is often a protobuf Map, convert to dict
                                            args = dict(part.function_call.args)
                                        elif hasattr(part.function_call, 'arguments'):
                                            # Handle potential alternative attribute name
                                            args = part.function_call.arguments
                                            if not isinstance(args, dict): # Ensure it's a dict
                                                args = {}

                                        if name:
                                            result["tool_calls"].append({
                                                "name": name,
                                                "arguments": args
                                            })
                                        else:
                                             logger.warning("Found function_call part without a name.")

                                    except Exception as e:
                                        logger.warning(f"Error extracting function call details: {e}")
                                else:
                                     logger.debug(f"Skipping unknown part type: {type(part)}")

            # Fallback: If no text extracted from parts, try response.text directly
            # This might still fail if the response *only* contains non-text parts like function calls
            if not result["text"] and not result["tool_calls"]:
                 try:
                     if hasattr(response, "text"):
                          result["text"] = response.text
                 except Exception as e:
                     logger.warning(f"Could not access response.text directly: {e}")

            # If text is still empty but we have tool calls, set a placeholder message
            if not result["text"] and result["tool_calls"]:
                result["text"] = "Okay, I will use the requested tool." # More specific placeholder

        except AttributeError as ae:
             logger.error(f"Attribute error processing Gemini response structure: {ae}. Response object might be unexpected.")
             result["text"] = "I encountered an issue understanding the response structure."
        except Exception as e:
            logger.error(f"General error processing Gemini response: {e}")
            result["text"] = "I encountered an error processing the response."
        
        logger.debug(f"Processed response: {result}")
        return result

    async def chat(self, 
            messages: List[Dict[str, Any]], 
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Have a chat conversation with the Gemini model.

        Args:
            messages: List of messages in the conversation so far.
                     Each message should have 'role' (user or assistant) and 'content'.
            temperature: Temperature for sampling. Higher values make output more random.
            max_tokens: Maximum number of tokens to generate.
            tools: List of tools to make available to the model.

        Returns:
            Generated response from the model.
        """
        if not self.model:
            self._initialize_model()
        
        # Format messages for Gemini API
        formatted_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                formatted_messages.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                formatted_messages.append({"role": "model", "parts": [{"text": content}]})
            elif role == "system":
                # Add system prompt as a user message at the beginning
                if not formatted_messages:
                    formatted_messages.append({"role": "user", "parts": [{"text": f"System: {content}"}]})
        
        # Get default values from configuration if not provided
        model_config = self.config.get_model_config()
        if temperature is None:
            temperature = model_config.get("temperature", 0.7)
        if max_tokens is None:
            max_tokens = model_config.get("max_tokens", 4096)
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            top_p=model_config.get("top_p", 0.95),
            top_k=model_config.get("top_k", 40),
            max_output_tokens=max_tokens
        )
        
        try:
            # Generate response
            if tools:
                # If tools are provided, enable function calling
                response = await self.model.generate_content_async(
                    formatted_messages,
                    generation_config=generation_config,
                    tools=tools
                )
            else:
                # Standard chat without tools
                response = await self.model.generate_content_async(
                    formatted_messages,
                    generation_config=generation_config
                )
                
            return self._process_response(response)
        except Exception as e:
            logger.error(f"Error in chat with Gemini: {e}")
            raise

# Create a singleton instance
gemini_client = GeminiClient()


def get_gemini_client() -> GeminiClient:
    """Get the Gemini client instance."""
    return gemini_client 