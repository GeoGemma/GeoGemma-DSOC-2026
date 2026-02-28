"""
Memory management for the Gemini client.

This module provides functionality for storing and managing conversation history
for the Gemini model, allowing for persistent memory across interactions.
"""

import logging
import time
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ChatHistory:
    """
    Class for managing conversation history for the Gemini model.
    
    This class provides functionality to store and retrieve conversation history,
    organized by session IDs, with support for:
    - Adding messages to history
    - Retrieving history for a specific session
    - Pruning old or large histories
    - Adding system prompts
    """
    
    def __init__(self, max_history_length: int = 20, max_sessions: int = 1000):
        """
        Initialize the chat history manager.
        
        Args:
            max_history_length: Maximum number of messages to keep per session.
            max_sessions: Maximum number of sessions to track.
        """
        self.histories: Dict[str, List[Dict[str, Any]]] = {}
        self.session_timestamps: Dict[str, float] = {}
        self.max_history_length = max_history_length
        self.max_sessions = max_sessions
        
        # System prompt (can be customized)
        self.system_prompt = (
            "You are a helpful GIS and sustainability analysis assistant. "
            "You have access to various tools for analyzing geographic data, "
            "weather information, environmental metrics, and visualization capabilities. "
            "Provide accurate and helpful responses, and use appropriate tools when needed."
        )
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session.
            role: Role of the message sender ('user' or 'assistant').
            content: Text content of the message.
        """
        if role not in ['user', 'assistant', 'system']:
            logger.warning(f"Invalid role '{role}', defaulting to 'user'")
            role = 'user'
        
        # Initialize history for new sessions with system prompt
        if session_id not in self.histories:
            self.histories[session_id] = []
            # Add system prompt if this is a new session
            self.histories[session_id].append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add the message
        self.histories[session_id].append({
            "role": role,
            "content": content
        })
        
        # Update session timestamp
        self.session_timestamps[session_id] = time.time()
        
        # Prune history if needed
        if len(self.histories[session_id]) > self.max_history_length + 1:  # +1 for system message
            # Keep system message and trim oldest messages
            system_message = None
            if self.histories[session_id][0]["role"] == "system":
                system_message = self.histories[session_id][0]
                self.histories[session_id] = self.histories[session_id][-(self.max_history_length):]
                self.histories[session_id].insert(0, system_message)
            else:
                self.histories[session_id] = self.histories[session_id][-(self.max_history_length):]
        
        # Prune old sessions if needed
        if len(self.histories) > self.max_sessions:
            self._prune_old_sessions()
    
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session.
            
        Returns:
            List of message dictionaries for the session, or an empty list if no history exists.
        """
        # Update timestamp if session exists
        if session_id in self.histories:
            self.session_timestamps[session_id] = time.time()
            return self.histories[session_id]
        return []
    
    def clear_history(self, session_id: str) -> bool:
        """
        Clear the conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session.
            
        Returns:
            True if history was cleared, False if session not found.
        """
        if session_id in self.histories:
            del self.histories[session_id]
            if session_id in self.session_timestamps:
                del self.session_timestamps[session_id]
            return True
        return False
    
    def _prune_old_sessions(self) -> None:
        """
        Remove the oldest sessions when the number of sessions exceeds the maximum.
        """
        if len(self.histories) <= self.max_sessions:
            return
        
        # Sort sessions by timestamp (oldest first)
        sorted_sessions = sorted(
            self.session_timestamps.items(),
            key=lambda x: x[1]
        )
        
        # Remove oldest sessions until we're under the limit
        sessions_to_remove = len(self.histories) - self.max_sessions
        for i in range(sessions_to_remove):
            if i < len(sorted_sessions):
                session_id = sorted_sessions[i][0]
                if session_id in self.histories:
                    del self.histories[session_id]
                if session_id in self.session_timestamps:
                    del self.session_timestamps[session_id]
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt used for new conversations.
        
        Args:
            prompt: The system prompt to use.
        """
        self.system_prompt = prompt
    
    def update_system_prompt(self, session_id: str, prompt: str) -> bool:
        """
        Update the system prompt for an existing session.
        
        Args:
            session_id: Unique identifier for the conversation session.
            prompt: The new system prompt to use.
            
        Returns:
            True if updated successfully, False if session not found.
        """
        if session_id not in self.histories:
            return False
        
        # Find and update system message if it exists
        for i, message in enumerate(self.histories[session_id]):
            if message["role"] == "system":
                self.histories[session_id][i]["content"] = prompt
                return True
        
        # Add system message if it doesn't exist
        self.histories[session_id].insert(0, {
            "role": "system",
            "content": prompt
        })
        return True


# Create a singleton instance
chat_history = ChatHistory()

def get_chat_history() -> ChatHistory:
    """Get the chat history manager instance."""
    return chat_history 