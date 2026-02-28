"""
MCP Server implementation for the GIS AI Agent.

This module provides the core server implementation for the Model Context Protocol,
allowing the agent to expose tools to LLMs and handle tool calls.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Callable, Optional, Union, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..config import get_config
from ..gemini.client import get_gemini_client
from ..gemini.memory import get_chat_history
from .tools import get_all_tools, get_tool_schemas
from ..tools.climate_analysis import climate_analysis_tools
from ..tools.resilience_planning import resilience_planning_tools
from ..utils import (
    get_connection_manager,
    get_query_rate_limiter,
    get_tool_call_rate_limiter,
    get_input_validator,
    get_tool_executor,
    get_cache,
    QueryMessage,
    ToolCallMessage,
    ClearHistoryMessage,
    schedule_cache_maintenance
)

# Configure logging
logger = logging.getLogger(__name__)

class MCPServer:
    """Model Context Protocol server implementation."""

    def __init__(self, name: str = "GIS AI Agent"):
        """
        Initialize the MCP server.

        Args:
            name: Name of the MCP server.
        """
        self.name = name
        
        # Load configuration
        self.config = get_config()
        server_config = self.config.get_server_config().get("server", {})
        
        # Set server properties
        self.host = server_config.get("host", "0.0.0.0")
        self.port = server_config.get("port", 8080)
        self.debug = server_config.get("debug", False)
        
        # Initialize FastAPI app
        self.app = FastAPI(title=f"{name} MCP Server", 
                          docs_url="/api/docs",
                          redoc_url="/api/redoc",
                          openapi_url="/api/openapi.json")
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=server_config.get("cors_origins", ["https://example.com"]),  # Restrict to specific domains
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],  # Restrict to necessary methods
            allow_headers=["Content-Type", "Authorization"],  # Restrict to necessary headers
        )
        
        # Load tools
        self.tools = get_all_tools()
        
        # Manually add climate analysis tools
        for name, tool in climate_analysis_tools.items():
            self.tools[name] = tool
            logger.info(f"Added climate analysis tool: {name}")
        
        # Manually add resilience planning tools
        for name, tool in resilience_planning_tools.items():
            self.tools[name] = tool
            logger.info(f"Added resilience planning tool: {name}")
            
        # Initialize tool executor with tools
        self.tool_executor = get_tool_executor(self.tools)
        
        # Get service instances
        self.connection_manager = get_connection_manager()
        self.chat_history = get_chat_history()
        self.query_rate_limiter = get_query_rate_limiter()
        self.tool_call_rate_limiter = get_tool_call_rate_limiter()
        self.validator = get_input_validator()
        
        # Set up routes
        self._setup_routes()
        
        # Schedule cache maintenance
        schedule_cache_maintenance()
        
        logger.info(f"MCP Server '{name}' initialized with {len(self.tools)} tools")
    
    def _setup_routes(self):
        """Set up API routes for the server."""
        @self.app.get("/")
        async def root():
            return {
                "name": self.name, 
                "version": "0.2.0", 
                "status": "running",
                "tools_count": len(self.tools)
            }
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": time.time()}
        
        @self.app.get("/tools")
        async def get_tools():
            tool_list = []
            for name, tool in self.tools.items():
                tool_list.append({
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })
            return {"tools": tool_list}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            # Connect and get session ID
            try:
                session_id = await self.connection_manager.connect(websocket)
            except ValueError as e:
                logger.warning(f"Connection rejected: {e}")
                return
            
            try:
                # Send session info to client
                await websocket.send_json({
                    "type": "session_info",
                    "session_id": session_id
                })
                
                # Handle messages
                while True:
                    # Receive message
                    data = await websocket.receive_json()
                    
                    # Add session_id to the message if not provided
                    if "session_id" not in data:
                        data["session_id"] = session_id
                    
                    # Update activity timestamp in session 
                    self.connection_manager.update_activity(session_id)
                    
                    # Process the message
                    response = await self._handle_websocket_message(data)
                    
                    # Log response before sending
                    logger.debug(f"Sending response back via WebSocket: {response}")
                    await websocket.send_json(response)
            
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {session_id}")
                await self.connection_manager.disconnect(session_id)
            
            except Exception as e:
                logger.error(f"Error in WebSocket connection: {e}")
                try:
                    await websocket.close(code=1011, reason=f"Internal server error: {str(e)[:50]}")
                except:
                    pass
                await self.connection_manager.disconnect(session_id)
    
    async def _handle_websocket_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a message received through the WebSocket connection.

        Args:
            data: The message received from the client.

        Returns:
            Response message to send back to the client.
        """
        session_id = data.get("session_id", "default")
        
        # Determine message type and validate
        message_type = data.get("type")
        
        if message_type == "query":
            # Validate query message format
            validated_data = self.validator.validate_model(data, QueryMessage)
            if not validated_data:
                return self._format_error_response(session_id, "Invalid query format")
            
            # Apply rate limiting
            if not self.query_rate_limiter.can_request(session_id):
                logger.warning(f"Rate limit exceeded for session {session_id}")
                return self._format_error_response(session_id, "Rate limit exceeded. Please try again later.")
            
            # Extract the query
            query = data.get("query", "")
            if not query:
                return self._format_error_response(session_id, "No query provided")
            
            try:
                # Get the Gemini client
                gemini_client = get_gemini_client()
                
                # Format tools for Gemini API
                gemini_tools = self._prepare_tools_for_gemini()
                
                # Add the user's message to the chat history
                self.chat_history.add_message(session_id, "user", query)
                
                # Get the conversation history for this session
                conversation_history = self.chat_history.get_history(session_id)
                
                logger.info(f"Using chat history for session {session_id} with {len(conversation_history)} messages")
                
                # Generate response from Gemini using chat with history
                llm_response = await gemini_client.chat(
                    messages=conversation_history,
                    tools=gemini_tools
                )
                logger.debug(f"LLM response received: {llm_response}")
                
                # Add the assistant's response to chat history
                if llm_response.get("text"):
                    self.chat_history.add_message(session_id, "assistant", llm_response.get("text"))
                
                # Check if the LLM requested a tool call
                tool_calls = llm_response.get("tool_calls")
                if tool_calls:
                    # Currently handling only the first tool call if multiple are present
                    # TODO: Extend to handle multiple sequential/parallel tool calls if needed
                    tool_call = tool_calls[0]
                    tool_name = tool_call.get("name")
                    arguments = tool_call.get("arguments", {})
                    
                    logger.info(f"LLM requested tool call: {tool_name} with args: {arguments}")
                    
                    if tool_name in self.tools:
                        try:
                            # Execute the tool using the tool executor
                            tool_result = await self.tool_executor.execute_tool(
                                tool_name,
                                arguments,
                                use_cache=True
                            )
                            logger.info(f"Tool {tool_name} executed successfully.")
                            
                            # Check if the tool failed (returned an error)
                            if isinstance(tool_result, dict) and "error" in tool_result:
                                logger.warning(f"Tool {tool_name} returned an error: {tool_result['error']}")
                                
                                # Use Gemini fallback for tool execution failures
                                # Focus on useful parameters rather than errors
                                response_message = await self._handle_tool_failure(
                                    session_id,
                                    tool_name,
                                    query,
                                    arguments,
                                    tool_result['error']
                                )
                                
                                return response_message
                            
                            else:
                                # Tool executed successfully without errors
                                # Add the tool result to chat history
                                tool_result_text = f"Tool '{tool_name}' result: {json.dumps(tool_result)}"
                                self.chat_history.add_message(session_id, "assistant", tool_result_text)
                                
                                # Get AI analysis of the tool results
                                analysis = await self._analyze_tool_result(session_id, tool_name, arguments, tool_result)
                                logger.info(f"Generated analysis for {tool_name} results")
                                
                                # Send tool result and analysis back to client
                                response_message = self._format_tool_response(
                                    session_id,
                                    tool_name,
                                    arguments,
                                    tool_result,
                                    analysis,
                                    False
                                )
                                
                                return response_message
                            
                        except Exception as tool_e:
                            logger.error(f"Error executing tool {tool_name}: {tool_e}")
                            
                            # Use Gemini fallback for tool execution exceptions
                            response_message = await self._handle_tool_failure(
                                session_id,
                                tool_name,
                                query,
                                arguments,
                                str(tool_e)
                            )
                            
                            return response_message
                    else:
                        logger.warning(f"LLM requested unknown tool: {tool_name}")
                        # Instead of returning an error, use Gemini fallback
                        response_message = await self._handle_generic_query_fallback(
                            session_id,
                            query
                        )
                        
                        return response_message
                        
                else:
                    # No tool call, check if the response is empty or generic
                    response_text = llm_response.get("text", "").strip().lower()
                    generic_responses = [
                        "i don't know", 
                        "i don't have", 
                        "no tool found", 
                        "no data available",
                        "i don't have access",
                        "i cannot access",
                        "i do not have the necessary",
                        "there is no specific tool",
                        "i'm unable to provide"
                    ]
                    
                    is_generic_response = not response_text or any(phrase in response_text for phrase in generic_responses)
                    
                    if is_generic_response:
                        # Use Gemini fallback for generic responses
                        response_message = await self._handle_generic_query_fallback(
                            session_id,
                            query
                        )
                        
                        return response_message
                    else:
                        # Regular non-empty, non-generic response
                        response_message = {
                            "type": "response",
                            "query": query,
                            "response": llm_response.get("text", ""),
                            "session_id": session_id
                        }
                        
                        # Log response before sending
                        logger.debug(f"Sending response back via WebSocket: {response_message}")
                        return response_message

            except asyncio.TimeoutError:
                logger.error(f"Request timed out for session {session_id}")
                return self._format_error_response(session_id, "Request timed out. Please try again.")
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                return self._format_error_response(session_id, str(e))
                
        elif message_type == "clear_history":
            # Validate clear history message format
            validated_data = self.validator.validate_model(data, ClearHistoryMessage)
            if not validated_data:
                return self._format_error_response(session_id, "Invalid clear_history format")
            
            # Clear chat history from memory
            success = self.chat_history.clear_history(session_id)
            
            return {
                "type": "history_cleared", 
                "success": success,
                "session_id": session_id
            }

        elif message_type == "tool_call":
            # Validate tool call message format
            validated_data = self.validator.validate_model(data, ToolCallMessage)
            if not validated_data:
                return self._format_error_response(session_id, "Invalid tool_call format")
            
            # Apply rate limiting
            if not self.tool_call_rate_limiter.can_request(session_id):
                logger.warning(f"Tool call rate limit exceeded for session {session_id}")
                return self._format_error_response(session_id, "Rate limit exceeded for tool calls. Please try again later.")
            
            tool_name = data.get("tool_name", "")
            arguments = data.get("arguments", {})
            
            if not tool_name:
                return self._format_error_response(session_id, "No tool name provided")
            
            if tool_name not in self.tools:
                return self._format_error_response(session_id, f"Tool not found: {tool_name}")
            
            try:
                # Execute the tool using the tool executor
                tool_result = await self.tool_executor.execute_tool(
                    tool_name,
                    arguments,
                    use_cache=True
                )
                
                # Check if the tool failed (returned an error)
                if isinstance(tool_result, dict) and "error" in tool_result:
                    logger.warning(f"Direct tool call {tool_name} returned an error: {tool_result['error']}")
                    
                    # Use Gemini fallback for tool execution failures
                    # Focus on useful parameters rather than errors
                    response_message = await self._handle_tool_failure(
                        session_id,
                        tool_name,
                        query,
                        arguments,
                        tool_result['error']
                    )
                    
                    return response_message
                
                # Add tool call and result to history
                tool_call_text = f"Tool call: {tool_name} with arguments: {json.dumps(arguments)}"
                self.chat_history.add_message(session_id, "user", tool_call_text)
                
                tool_result_text = f"Tool result: {json.dumps(tool_result)}"
                self.chat_history.add_message(session_id, "assistant", tool_result_text)
                
                # Get AI analysis of the tool results
                analysis = await self._analyze_tool_result(session_id, tool_name, arguments, tool_result)
                logger.info(f"Generated analysis for direct {tool_name} call results")
                
                return self._format_tool_response(
                    session_id,
                    tool_name,
                    arguments,
                    tool_result,
                    analysis,
                    False
                )
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                
                # Use Gemini fallback for tool execution exceptions
                response_message = await self._handle_tool_failure(
                    session_id,
                    tool_name,
                    query,
                    arguments,
                    str(e)
                )
                
                return response_message
        
        else:
            return {"error": f"Unknown message type: {message_type}", "session_id": session_id}
    
    def _prepare_tools_for_gemini(self) -> List[Dict[str, Any]]:
        """
        Format tools for the Gemini API.
        
        Returns:
            List of tool objects formatted for Gemini.
        """
        gemini_tools = []
        for name, tool in self.tools.items():
            # Get the parameters and sanitize them for Gemini API
            parameters = self._sanitize_schema_for_gemini(tool.get("parameters", {}))
            
            # Only add required properties that Gemini API expects
            gemini_tools.append({
                "function_declarations": [{
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": {
                        "type": parameters.get("type", "object"),
                        "properties": parameters.get("properties", {}),
                        "required": parameters.get("required", [])
                    }
                }]
            })
        
        return gemini_tools
    
    def register_tool(self, 
                     name: str, 
                     function: Callable[[Dict[str, Any]], Any], 
                     description: str,
                     parameters: Dict[str, Any]) -> None:
        """
        Register a tool with the MCP server.

        Args:
            name: Name of the tool.
            function: Function that implements the tool.
            description: Description of what the tool does.
            parameters: Parameters that the tool accepts in JSON Schema format.
        """
        self.tools[name] = {
            "function": function,
            "description": description,
            "parameters": parameters
        }
        
        logger.info(f"Registered tool: {name}")
    
    async def run(self) -> None:
        """Run the MCP server."""
        # Start connection monitoring
        self.connection_manager.start_monitoring()
        
        # Create server configuration
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="debug" if self.debug else "info",
            reload=self.debug
        )
        
        # Create server
        server = uvicorn.Server(config)
        
        # Start server
        await server.serve()

    def _sanitize_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize JSON Schema for Gemini API by removing unsupported fields.
        
        Args:
            schema: Original JSON Schema
            
        Returns:
            Sanitized schema compatible with Gemini API
        """
        # Make a copy to avoid modifying the original
        sanitized = dict(schema)
        
        # Remove unsupported validation keywords
        unsupported_keywords = ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", 
                               "minLength", "maxLength", "pattern", "minItems", "maxItems",
                               "uniqueItems", "format"]
        
        for keyword in unsupported_keywords:
            if keyword in sanitized:
                del sanitized[keyword]
        
        # Recursively sanitize nested properties
        if "properties" in sanitized and isinstance(sanitized["properties"], dict):
            for prop_name, prop_schema in sanitized["properties"].items():
                if isinstance(prop_schema, dict):
                    sanitized["properties"][prop_name] = self._sanitize_schema_for_gemini(prop_schema)
        
        # Handle items in arrays
        if "items" in sanitized and isinstance(sanitized["items"], dict):
            sanitized["items"] = self._sanitize_schema_for_gemini(sanitized["items"])
            
        return sanitized

    async def _analyze_tool_result(self, session_id: str, tool_name: str, arguments: Dict[str, Any], tool_result: Dict[str, Any]) -> str:
        """
        Send tool results back to Gemini for further analysis.
        
        Args:
            session_id: Unique identifier for the conversation session.
            tool_name: The name of the tool that was executed.
            arguments: The arguments used to call the tool.
            tool_result: The raw result returned by the tool.
            
        Returns:
            A string containing the AI's analysis of the tool results.
        """
        try:
            # Get the Gemini client
            gemini_client = get_gemini_client()
            
            # Format the analysis prompt
            analysis_prompt = f"""Based on the results of the tool '{tool_name}', provide a detailed analysis and insights.
            
Tool: {tool_name}
Arguments: {json.dumps(arguments, indent=2)}
Result: {json.dumps(tool_result, indent=2)}

Please analyze this data and provide relevant insights, trends, and explanations. Focus on:
1. Key findings and patterns in the data
2. Any noteworthy observations 
3. Contextual information to help understand the results
4. Potential implications or recommendations

Your analysis:"""

            # Add this interaction to chat history as system message
            self.chat_history.add_message(
                session_id, 
                "system", 
                f"Request for analysis of {tool_name} results with arguments {arguments}"
            )
            
            # Get conversation history
            conversation_history = self.chat_history.get_history(session_id)
            # Add the analysis prompt as the most recent message
            conversation_history.append({
                "role": "user",
                "content": analysis_prompt
            })
            
            # Generate analysis from Gemini
            logger.info(f"Requesting analysis of {tool_name} results from Gemini")
            analysis_response = await gemini_client.chat(
                messages=conversation_history,
                # No tools for the analysis to keep it focused
            )
            
            analysis_text = analysis_response.get("text", "I couldn't generate an analysis of these results.")
            
            # Add the analysis to chat history
            self.chat_history.add_message(session_id, "assistant", analysis_text)
            
            return analysis_text
            
        except Exception as e:
            logger.error(f"Error analyzing tool results: {e}")
            return f"Error generating analysis: {str(e)}"

    async def _handle_tool_failure(self, 
                                session_id: str, 
                                tool_name: str, 
                                query: str, 
                                arguments: Dict[str, Any],
                                error: str) -> Dict[str, Any]:
        """
        Handle a tool failure by using Gemini fallback.
        
        Args:
            session_id: Client session ID
            tool_name: Name of the tool that failed
            query: Original query
            arguments: Arguments for the tool
            error: Error message
            
        Returns:
            Response message for the client
        """
        try:
            # Extract area info for context
            area = arguments.get('area', arguments.get('region', ''))
            
            # Form a query that doesn't mention the error
            effective_query = (
                f"Information about {area if area else ''} {tool_name}" 
                if area else query
            )
            
            # Form context without mentioning error
            context = f"Target area: {area}. Tool: {tool_name}. Parameters: {json.dumps(arguments)}"
            
            # Call analyze_query_with_gemini as fallback
            fallback_result = await self.tool_executor.execute_tool(
                "analyze_query_with_gemini",
                {"query": effective_query, "context": context},
                use_cache=False
            )
            
            logger.info(f"Using Gemini fallback analysis for {tool_name}")
            
            # Add the fallback result to chat history
            self.chat_history.add_message(
                session_id, 
                "assistant", 
                f"Analysis: {fallback_result.get('analysis', '')}"
            )
            
            # Return formatted response
            return self._format_tool_response(
                session_id,
                tool_name,
                arguments,
                {
                    "success": True,
                    "message": f"Analysis data for {area if area else 'requested information'}",
                    "fallback_used": True
                },
                fallback_result.get("analysis", ""),
                True
            )
            
        except Exception as fallback_e:
            logger.error(f"Error using Gemini fallback: {fallback_e}")
            return self._format_error_response(session_id, f"Could not analyze {tool_name} data")
            
    async def _handle_generic_query_fallback(self, 
                                      session_id: str,
                                      query: str) -> Dict[str, Any]:
        """
        Handle a generic query with Gemini fallback when no specific tool matches.
        
        Args:
            session_id: Client session ID
            query: User's original query
            
        Returns:
            Response message for the client
        """
        try:
            # Call analyze_query_with_gemini as fallback
            fallback_result = await self.tool_executor.execute_tool(
                "analyze_query_with_gemini",
                {"query": query, "context": "Query relates to GIS data analysis."},
                use_cache=False
            )
            
            logger.info(f"Using Gemini fallback analysis for generic query")
            
            # Add the fallback result to chat history
            self.chat_history.add_message(
                session_id, 
                "assistant", 
                f"Analysis: {fallback_result.get('analysis', '')}"
            )
            
            # Return formatted response
            return self._format_tool_response(
                session_id,
                "GIS_Analysis",
                {},
                {
                    "success": True,
                    "message": "GIS data analysis",
                    "fallback_used": True
                },
                fallback_result.get("analysis", ""),
                True
            )
            
        except Exception as fallback_e:
            logger.error(f"Error using Gemini fallback: {fallback_e}")
            return self._format_error_response(session_id, "Could not analyze the requested data")

    def _format_tool_response(self, 
                            session_id: str,
                            tool_name: str, 
                            arguments: Dict[str, Any], 
                            result: Dict[str, Any], 
                            analysis: str,
                            is_fallback: bool = False) -> Dict[str, Any]:
        """
        Format a tool response in a consistent structure.
        
        Args:
            session_id: Client session ID
            tool_name: Name of the tool used
            arguments: Tool arguments
            result: Result from the tool execution
            analysis: Analysis of the results
            is_fallback: Whether this is a fallback response
            
        Returns:
            Formatted response message
        """
        message = {
            "type": "tool_result_with_analysis",
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result if not is_fallback else {
                "success": True,
                "message": f"Analysis data for {arguments.get('area', arguments.get('region', 'requested information'))}",
                "fallback_used": True
            },
            "analysis": analysis,
            "session_id": session_id
        }
        
        # Log response before sending
        logger.debug(f"Sending response back via WebSocket: {message}")
        return message

    def _format_error_response(self, session_id: str, error_message: str) -> Dict[str, Any]:
        """
        Format an error response consistently.
        
        Args:
            session_id: Client session ID
            error_message: Error message to display
            
        Returns:
            Formatted error response
        """
        response = {
            "error": error_message,
            "session_id": session_id
        }
        
        # Log response before sending
        logger.debug(f"Sending error response: {response}")
        return response


def create_server(name: str = "GIS AI Agent") -> MCPServer:
    """
    Create a new MCP server instance.

    Args:
        name: Name of the MCP server.

    Returns:
        An initialized MCPServer instance.
    """
    return MCPServer(name) 