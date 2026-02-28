# Chat Memory and Persistent Context

This document explains the chat memory feature in the GIS Agent, which allows the AI to remember previous conversations and maintain context across interactions.

## Overview

The GIS Agent now has a persistent memory system that lets it remember previous messages in a conversation. This enables more natural, contextual interactions where the AI can refer back to earlier parts of the conversation.

## Key Features

- **Session-Based Memory**: Each user connection gets a unique session ID
- **Persistent Context**: The AI can reference previous messages within a session
- **Local Storage**: Session IDs are saved in the browser's local storage to maintain sessions across page reloads
- **History Management**: Users can clear their conversation history when desired
- **System Prompts**: Each conversation starts with a system prompt that provides context and instructions to the AI

## How It Works

1. **Session Creation**: When a user connects, they're assigned a unique session ID
2. **Message Storage**: Each message (from both the user and the AI) is stored in memory
3. **Context Inclusion**: When the user sends a new message, the entire conversation history is sent to the AI
4. **Tool Interaction**: Results from tool calls are also added to the conversation history
5. **Memory Management**: The system automatically manages memory size by limiting the number of messages per session

## User Interface

- A "Clear History" button allows users to reset the conversation
- Sessions persist across page reloads (using browser local storage)
- The welcome message appears only for new sessions

## Technical Implementation

### Server-Side

- The `ChatHistory` class in `src/gemini/memory.py` manages conversation histories
- The MCP server tracks active sessions and adds messages to the appropriate history
- The Gemini API's `chat()` method is used instead of `generate_text()` to leverage conversation history

### Client-Side

- WebSocket connections maintain a session ID
- The ID is stored in local storage for persistence
- The chat interface displays messages and allows clearing history

## Limitations

- There is a maximum number of messages per session (default: 20)
- There is a maximum number of sessions stored server-side (default: 1000)
- Very long conversation histories may approach token limits of the AI model

## Future Improvements

- Database persistence for histories across server restarts
- User authentication for more secure and personalized history management
- Summarization of long conversations to stay within token limits
- Fine-grained control over what parts of history to keep or discard 