"""
MCP Server module for the GIS AI Agent.

This module implements the Model Context Protocol server functionality,
allowing the agent to provide tools to LLMs and handle tool calls.
"""

# Initialize tools when this module is imported
from .tools import _initialize_tools

# Ensure tools are initialized
_initialize_tools() 