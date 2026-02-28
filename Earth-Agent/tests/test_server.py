"""
Tests for the MCP server implementation.

This module contains unit tests for the MCP server functionality.
"""

import os
import sys
import json
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to allow importing from the src module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mcp_server.server import create_server
from src.config import ConfigManager


class TestMCPServer(unittest.TestCase):
    """Test cases for the MCP server."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a ConfigManager with a test configuration
        self.config_mock = MagicMock(spec=ConfigManager)
        self.config_mock.get_server_config.return_value = {
            "server": {
                "host": "127.0.0.1",
                "port": 8080,
                "debug": True
            }
        }
        self.config_mock.get_api_keys.return_value = {
            "gemini": {
                "api_key": "test_api_key"
            }
        }
        self.config_mock.get_model_config.return_value = {
            "provider": "gemini",
            "model_name": "gemini-2.0-flash",
            "temperature": 0.7
        }
        self.config_mock.get_tool_config.return_value = {
            "spatial_query": {
                "enabled": True
            },
            "sustainability_assessment": {
                "enabled": True
            }
        }
        
        # Patch the config manager
        self.config_patcher = patch('src.mcp_server.server.get_config', return_value=self.config_mock)
        self.mock_get_config = self.config_patcher.start()
        
        # Patch the Gemini client
        self.gemini_client_patcher = patch('src.mcp_server.server.get_gemini_client')
        self.mock_gemini_client = self.gemini_client_patcher.start()
        
        # Patch the tools registry
        self.tools_patcher = patch('src.mcp_server.server.get_all_tools')
        self.mock_tools = self.tools_patcher.start()
        self.mock_tools.return_value = {
            "test_tool": {
                "function": MagicMock(return_value={"result": "Test result"}),
                "description": "Test tool",
                "parameters": {}
            }
        }
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.config_patcher.stop()
        self.gemini_client_patcher.stop()
        self.tools_patcher.stop()
    
    def test_server_creation(self):
        """Test server creation with the correct configuration."""
        server = create_server(name="Test MCP Server")
        
        # Check server attributes
        self.assertEqual(server.name, "Test MCP Server")
        self.assertEqual(server.host, "127.0.0.1")
        self.assertEqual(server.port, 8080)
        self.assertTrue(server.debug)
    
    def test_register_tool(self):
        """Test registering a tool with the server."""
        server = create_server(name="Test MCP Server")
        
        # Register a test tool
        test_function = MagicMock(return_value={"result": "Custom tool result"})
        server.register_tool(
            name="custom_tool",
            function=test_function,
            description="Custom test tool",
            parameters={"param1": {"type": "string"}}
        )
        
        # Check that the tool was registered
        self.assertIn("custom_tool", server.tools)
        self.assertEqual(server.tools["custom_tool"]["description"], "Custom test tool")
        self.assertEqual(server.tools["custom_tool"]["function"], test_function)
        self.assertEqual(server.tools["custom_tool"]["parameters"], {"param1": {"type": "string"}})


class TestAsyncMCPServer(unittest.IsolatedAsyncioTestCase):
    """Asynchronous test cases for the MCP server."""
    
    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        # Create a ConfigManager with a test configuration
        self.config_mock = MagicMock(spec=ConfigManager)
        self.config_mock.get_server_config.return_value = {
            "server": {
                "host": "127.0.0.1",
                "port": 8080,
                "debug": True
            }
        }
        self.config_mock.get_api_keys.return_value = {
            "gemini": {
                "api_key": "test_api_key"
            }
        }
        self.config_mock.get_model_config.return_value = {
            "provider": "gemini",
            "model_name": "gemini-2.0-flash",
            "temperature": 0.7
        }
        
        # Patch the config manager
        self.config_patcher = patch('src.mcp_server.server.get_config', return_value=self.config_mock)
        self.mock_get_config = self.config_patcher.start()
        
        # Patch the Gemini client
        self.gemini_client_patcher = patch('src.mcp_server.server.get_gemini_client')
        self.mock_gemini_client = self.gemini_client_patcher.start()
        
        # Create a mock async function for tool
        async def mock_tool_function(arguments):
            return {"result": "Async test result"}
        
        # Patch the tools registry
        self.tools_patcher = patch('src.mcp_server.server.get_all_tools')
        self.mock_tools = self.tools_patcher.start()
        self.mock_tools.return_value = {
            "async_test_tool": {
                "function": mock_tool_function,
                "description": "Async test tool",
                "parameters": {}
            }
        }
    
    async def asyncTearDown(self):
        """Tear down test fixtures after each test method."""
        self.config_patcher.stop()
        self.gemini_client_patcher.stop()
        self.tools_patcher.stop()
    
    async def test_tool_execution(self):
        """Test asynchronous tool execution."""
        server = create_server(name="Test MCP Server")
        
        # Get the test tool
        test_tool = server.tools["async_test_tool"]["function"]
        
        # Call the tool
        result = await test_tool({})
        
        # Check the result
        self.assertEqual(result, {"result": "Async test result"})


if __name__ == '__main__':
    unittest.main() 