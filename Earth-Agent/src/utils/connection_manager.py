"""
Connection manager module for the GIS AI Agent.

This module provides functionality for managing WebSocket connections and sessions,
including connection pooling, session hibernation, and reconnection.
"""

import asyncio
import logging
from typing import Dict, Set, Optional, List, Any, Callable, Awaitable
import time
import uuid
from fastapi import WebSocket, WebSocketDisconnect

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and sessions for the MCP server.
    
    This class is responsible for:
    - Managing active WebSocket connections
    - Tracking session activity and hibernation
    - Broadcasting messages to connected clients
    - Managing connection limits and timeouts
    """
    
    def __init__(self, 
                inactive_timeout: int = 1800,  # 30 minutes
                max_connections: int = 100,
                hibernation_timeout: int = 7200):  # 2 hours
        """
        Initialize the connection manager.
        
        Args:
            inactive_timeout: Time in seconds after which a session is considered inactive.
            max_connections: Maximum number of active connections allowed.
            hibernation_timeout: Time in seconds after which a hibernated session is removed.
        """
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> WebSocket
        self.connection_times: Dict[str, float] = {}  # session_id -> last_activity_time
        self.hibernated_sessions: Dict[str, float] = {}  # session_id -> hibernation_time
        
        self.inactive_timeout = inactive_timeout
        self.max_connections = max_connections
        self.hibernation_timeout = hibernation_timeout
        self._monitor_task = None
        
        logger.info(f"ConnectionManager initialized with {max_connections} max connections")
    
    def start_monitoring(self) -> None:
        """
        Start the session monitoring task.
        This should be called after an event loop is running.
        """
        if self._monitor_task is None:
            try:
                self._monitor_task = asyncio.create_task(self._monitor_sessions())
                logger.info("Session monitoring started")
            except RuntimeError as e:
                logger.warning(f"Cannot start session monitoring: {e}")
                logger.warning("Session monitoring will be started on first connection")
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register.
            
        Returns:
            The session ID assigned to this connection.
        """
        # Start monitoring if not already started
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_sessions())
            logger.info("Session monitoring started during first connection")
            
        # Check if we're at max capacity
        if len(self.active_connections) >= self.max_connections:
            # Try to free up some connections
            await self._hibernate_inactive_connections()
            
            # If still at capacity, reject the connection
            if len(self.active_connections) >= self.max_connections:
                logger.warning("Connection rejected: maximum connections reached")
                await websocket.close(code=1008, reason="Server at capacity")
                raise ValueError("Maximum connections reached")
        
        # Generate a session ID
        session_id = str(uuid.uuid4())
        
        # Accept the connection
        await websocket.accept()
        
        # Check for hibernated session (future enhancement)
        # We could restore session data here if the client provides a previous session ID
        
        # Register the connection
        self.active_connections[session_id] = websocket
        self.connection_times[session_id] = time.time()
        
        logger.info(f"Client connected with session ID: {session_id}")
        return session_id
    
    async def disconnect(self, session_id: str) -> None:
        """
        Unregister a WebSocket connection.
        
        Args:
            session_id: The session ID to unregister.
        """
        if session_id in self.active_connections:
            # Move to hibernated state instead of complete removal
            self.hibernated_sessions[session_id] = time.time()
            
            # Remove from active connections
            del self.active_connections[session_id]
            
            if session_id in self.connection_times:
                del self.connection_times[session_id]
                
            logger.info(f"Client disconnected, session hibernated: {session_id}")
    
    def is_connected(self, session_id: str) -> bool:
        """
        Check if a session is currently connected.
        
        Args:
            session_id: The session ID to check.
            
        Returns:
            True if the session is connected, False otherwise.
        """
        return session_id in self.active_connections
    
    async def send_json(self, session_id: str, message: Any) -> bool:
        """
        Send a JSON message to a specific client.
        
        Args:
            session_id: The session ID to send the message to.
            message: The message object to send.
            
        Returns:
            True if the message was sent, False if the session is not connected.
        """
        if session_id not in self.active_connections:
            return False
        
        try:
            # Update last activity time
            self.connection_times[session_id] = time.time()
            
            # Send the message
            await self.active_connections[session_id].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to session {session_id}: {e}")
            await self._handle_connection_error(session_id)
            return False
    
    async def broadcast_json(self, message: Any, exclude: Optional[List[str]] = None) -> None:
        """
        Broadcast a JSON message to all connected clients.
        
        Args:
            message: The message object to broadcast.
            exclude: List of session IDs to exclude from the broadcast.
        """
        exclude = exclude or []
        failed_sessions = []
        
        for session_id, websocket in self.active_connections.items():
            if session_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to session {session_id}: {e}")
                    failed_sessions.append(session_id)
        
        # Clean up failed connections
        for session_id in failed_sessions:
            await self._handle_connection_error(session_id)
    
    async def _handle_connection_error(self, session_id: str) -> None:
        """
        Handle a connection error for a specific session.
        
        Args:
            session_id: The session ID that experienced an error.
        """
        try:
            # Try to close the connection cleanly
            websocket = self.active_connections[session_id]
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass  # Connection might already be closed
        
        # Move the session to hibernated state
        await self.disconnect(session_id)
    
    def update_activity(self, session_id: str) -> None:
        """
        Update the last activity time for a session.
        
        Args:
            session_id: The session ID to update.
        """
        if session_id in self.active_connections:
            self.connection_times[session_id] = time.time()
    
    async def _hibernate_inactive_connections(self) -> int:
        """
        Hibernate inactive connections to free up resources.
        
        Returns:
            Number of connections hibernated.
        """
        current_time = time.time()
        inactive_sessions = [
            session_id for session_id, last_activity in self.connection_times.items()
            if current_time - last_activity > self.inactive_timeout
        ]
        
        count = 0
        for session_id in inactive_sessions:
            if session_id in self.active_connections:
                try:
                    websocket = self.active_connections[session_id]
                    await websocket.close(code=1000, reason="Session hibernated due to inactivity")
                    await self.disconnect(session_id)
                    count += 1
                except Exception as e:
                    logger.error(f"Error hibernating session {session_id}: {e}")
        
        if count > 0:
            logger.info(f"Hibernated {count} inactive connections")
        
        return count
    
    async def _cleanup_old_hibernated_sessions(self) -> int:
        """
        Clean up old hibernated sessions.
        
        Returns:
            Number of hibernated sessions removed.
        """
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, hibernation_time in self.hibernated_sessions.items()
            if current_time - hibernation_time > self.hibernation_timeout
        ]
        
        for session_id in expired_sessions:
            del self.hibernated_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Removed {len(expired_sessions)} expired hibernated sessions")
        
        return len(expired_sessions)
    
    async def _monitor_sessions(self) -> None:
        """Periodically monitor sessions for inactivity and cleanup."""
        while True:
            try:
                await self._hibernate_inactive_connections()
                await self._cleanup_old_hibernated_sessions()
            except Exception as e:
                logger.error(f"Error in session monitor: {e}")
            
            await asyncio.sleep(300)  # Run every 5 minutes


# Create a singleton instance
_connection_manager = ConnectionManager()

def get_connection_manager() -> ConnectionManager:
    """Get the connection manager instance."""
    return _connection_manager 