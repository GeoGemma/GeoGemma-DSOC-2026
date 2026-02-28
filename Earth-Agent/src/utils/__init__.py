"""
Utility functions and classes for the GIS AI Agent.

This module contains various utility functions and classes.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Callable, TypeVar, Type, Union

# Configure logging
logger = logging.getLogger(__name__)

# Import utilities
from .cache import get_cache, schedule_cache_maintenance
from .connection_manager import get_connection_manager
from .security import (
    get_query_rate_limiter,
    get_tool_call_rate_limiter,
    get_input_validator,
    QueryMessage,
    ToolCallMessage,
    ClearHistoryMessage
)
from .tool_executor import get_tool_executor

__all__ = [
    "get_cache",
    "get_connection_manager",
    "get_query_rate_limiter",
    "get_tool_call_rate_limiter",
    "get_input_validator",
    "get_tool_executor",
    "schedule_cache_maintenance",
    "QueryMessage",
    "ToolCallMessage",
    "ClearHistoryMessage"
] 