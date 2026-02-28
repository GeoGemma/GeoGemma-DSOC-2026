"""
Security module for the GIS AI Agent.

This module provides security features such as input validation, rate limiting,
and protection against common security vulnerabilities.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, TypeVar, cast, List, Type
from pydantic import BaseModel, ValidationError
import json

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')


class RateLimiter:
    """Rate limiter with token bucket algorithm for API protection."""
    
    def __init__(self, rate: float, per: float, burst: int = 1):
        """
        Initialize the rate limiter.
        
        Args:
            rate: Number of requests allowed in the time period.
            per: Time period in seconds.
            burst: Maximum token bucket size (bursts allowed).
        """
        self.rate = rate
        self.per = per
        self.burst = burst
        self.tokens: Dict[str, float] = {}  # client_id -> tokens
        self.last_refill: Dict[str, float] = {}  # client_id -> last_refill_time
    
    def _refill_tokens(self, client_id: str) -> None:
        """
        Refill tokens based on time elapsed since last refill.
        
        Args:
            client_id: The client identifier.
        """
        now = time.time()
        
        # If client not seen before, initialize tokens
        if client_id not in self.tokens:
            self.tokens[client_id] = self.burst
            self.last_refill[client_id] = now
            return
        
        # Calculate time since last refill
        last_time = self.last_refill[client_id]
        time_passed = now - last_time
        
        # Calculate tokens to add
        new_tokens = time_passed * (self.rate / self.per)
        
        # Update tokens (capped at burst limit)
        self.tokens[client_id] = min(self.burst, self.tokens[client_id] + new_tokens)
        self.last_refill[client_id] = now
    
    def can_request(self, client_id: str, tokens: float = 1.0) -> bool:
        """
        Check if a client can make a request.
        
        Args:
            client_id: The client identifier.
            tokens: Number of tokens to consume for this request.
            
        Returns:
            True if the request is allowed, False otherwise.
        """
        self._refill_tokens(client_id)
        
        if self.tokens[client_id] >= tokens:
            self.tokens[client_id] -= tokens
            return True
        
        return False
    
    async def wait_for_token(self, client_id: str, tokens: float = 1.0) -> bool:
        """
        Wait until a token is available for the client.
        
        Args:
            client_id: The client identifier.
            tokens: Number of tokens needed.
            
        Returns:
            True if a token became available, False on error.
        """
        # Check if we can request immediately
        if self.can_request(client_id, tokens):
            return True
        
        # If not, calculate how long to wait until enough tokens are available
        current_tokens = self.tokens[client_id]
        tokens_needed = tokens - current_tokens
        seconds_to_wait = tokens_needed / (self.rate / self.per)
        
        try:
            logger.debug(f"Rate limit hit for {client_id}, waiting {seconds_to_wait:.2f}s")
            await asyncio.sleep(seconds_to_wait)
            
            # Verify we can now request
            return self.can_request(client_id, tokens)
        except Exception as e:
            logger.error(f"Error waiting for rate limit: {e}")
            return False


class InputValidator:
    """Validates input data against Pydantic models."""
    
    @staticmethod
    def validate_model(data: Dict[str, Any], model: Type[BaseModel]) -> Optional[BaseModel]:
        """
        Validate data against a Pydantic model.
        
        Args:
            data: The data to validate.
            model: The Pydantic model to validate against.
            
        Returns:
            Validated model instance or None if validation fails.
        """
        try:
            # Parse and validate the data against the model
            validated_data = model.parse_obj(data)
            return validated_data
        except ValidationError as e:
            logger.warning(f"Data validation failed: {e}")
            return None
    
    @staticmethod
    def sanitize_json(json_str: str) -> Optional[Dict[str, Any]]:
        """
        Sanitize and validate a JSON string.
        
        Args:
            json_str: The JSON string to sanitize.
            
        Returns:
            Parsed JSON object or None if parsing fails.
        """
        if not isinstance(json_str, str):
            return None
        
        try:
            # Parse JSON into Python object
            data = json.loads(json_str)
            
            # Ensure it's a dictionary
            if not isinstance(data, dict):
                return None
                
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"JSON validation failed: {e}")
            return None


# Message models for validation
class QueryMessage(BaseModel):
    """Model for query messages."""
    type: str = "query"
    query: str
    session_id: Optional[str] = None


class ToolCallMessage(BaseModel):
    """Model for tool call messages."""
    type: str = "tool_call"
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None


class ClearHistoryMessage(BaseModel):
    """Model for clear history messages."""
    type: str = "clear_history"
    session_id: Optional[str] = None


# Create rate limiter instances for different operations
_query_rate_limiter = RateLimiter(rate=10, per=60, burst=15)  # 10 queries per minute, burst of 15
_tool_call_rate_limiter = RateLimiter(rate=20, per=60, burst=25)  # 20 tool calls per minute, burst of 25


def get_query_rate_limiter() -> RateLimiter:
    """Get the query rate limiter instance."""
    return _query_rate_limiter


def get_tool_call_rate_limiter() -> RateLimiter:
    """Get the tool call rate limiter instance."""
    return _tool_call_rate_limiter


# Validator instance
input_validator = InputValidator()


def get_input_validator() -> InputValidator:
    """Get the input validator instance."""
    return input_validator 