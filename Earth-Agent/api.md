# GIS Agent API Documentation

This document provides detailed information on how to integrate with the GIS Agent API in your frontend application.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [WebSocket API](#websocket-api)
  - [Connection Process](#connection-process)
  - [Message Types](#message-types)
  - [Response Formats](#response-formats)
- [REST API Endpoints](#rest-api-endpoints)
  - [Base Information](#base-information)
  - [Available Tools](#available-tools)
  - [Health Check Endpoints](#health-check-endpoints)
- [Available Tool Categories](#available-tool-categories)
  - [Spatial Query Tools](#spatial-query-tools)
  - [Weather Tools](#weather-tools)
  - [Sustainability Assessment Tools](#sustainability-assessment-tools)
  - [Visualization Tools](#visualization-tools)
  - [Climate Analysis Tools](#climate-analysis-tools)
  - [Resilience Planning Tools](#resilience-planning-tools)
- [Integration Examples](#integration-examples)
  - [JavaScript WebSocket Example](#javascript-websocket-example)
  - [React Integration Example](#react-integration-example)

## Base URL

The GIS Agent server is accessible at:

```
http://[host]:[port]
```

Replace `[host]` and `[port]` with your server's hostname/IP and port number.

## Authentication

The GIS Agent uses session-based authentication through the WebSocket connection. When connecting, the server will provide a session ID that should be used for subsequent requests.

## WebSocket API

The primary way to interact with the GIS Agent is through WebSockets for real-time communication.

### Connection Process

**Endpoint:** `/ws`

1. Connect to the WebSocket endpoint
2. The server will send a `session_info` message with your `session_id`
3. If you have previous chat history, it will be loaded from Firebase
4. Use the session ID for all subsequent messages

### Message Types

#### 1. Query Message

Send natural language queries to the AI:

```json
{
  "type": "query",
  "session_id": "your_session_id",
  "query": "Your question or command here"
}
```

Example queries:
- "What is the population of New York City?"
- "Calculate the distance between Paris and London"
- "Show me a map of earthquake risks in California"
- "What are the sustainability trends in urban planning?"

#### 2. Tool Call Message

Directly call specific tools with parameters:

```json
{
  "type": "tool_call",
  "session_id": "your_session_id",
  "tool_name": "name_of_tool",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

#### 3. Clear History Message

Clear the chat history for the session:

```json
{
  "type": "clear_history",
  "session_id": "your_session_id"
}
```

### Response Formats

#### 1. Session Info Response

Sent when a connection is established:

```json
{
  "type": "session_info",
  "session_id": "unique_session_id"
}
```

#### 2. Query Response

Response to a query message:

```json
{
  "type": "response",
  "session_id": "your_session_id",
  "content": "Response text from the AI",
  "timestamp": 1686840000
}
```

#### 3. Tool Result Response

Response when a tool is called (either directly or through a query):

```json
{
  "type": "tool_result",
  "session_id": "your_session_id",
  "tool_name": "name_of_tool",
  "result": {
    // Tool-specific result data
  },
  "analysis": "AI's analysis of the tool result",
  "timestamp": 1686840000
}
```

#### 4. Error Response

Sent when an error occurs:

```json
{
  "type": "error",
  "session_id": "your_session_id",
  "error": "Error message describing the issue",
  "timestamp": 1686840000
}
```

## REST API Endpoints

### Base Information

**Endpoint:** `GET /`

Returns basic information about the server.

**Response:**
```json
{
  "name": "GIS AI Agent",
  "version": "0.2.0",
  "status": "running",
  "tools_count": 30
}
```

### Available Tools

**Endpoint:** `GET /tools`

Returns a list of all available tools and their descriptions.

**Response:**
```json
{
  "tools": [
    {
      "name": "get_location_info",
      "description": "Get information about a specific location using GeoPy",
      "parameters": {
        "location": {
          "type": "string",
          "description": "Location name or coordinates"
        },
        "info_types": {
          "type": "array",
          "description": "List of information types to retrieve",
          "items": {
            "type": "string",
            "enum": ["basic", "administrative", "elevation", "timezone", "demographics"]
          }
        }
      }
    },
    // More tools...
  ]
}
```

### Health Check Endpoints

#### Basic Health

**Endpoint:** `GET /health`

Returns the current health status of the server.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "uptime_seconds": 1234,
  "hostname": "server_hostname",
  "environment": "production",
  "timestamp": 1686840000,
  "python_version": "3.10.8",
  "platform": "Linux-5.15.0-x86_64",
  "dependencies": {
    "fastapi": {"version": "0.115.12", "status": "installed"},
    "pydantic": {"version": "2.11.4", "status": "installed"},
    "google-generativeai": {"version": "0.8.5", "status": "installed"},
    "earthengine-api": {"version": "1.5.14", "status": "installed"},
    "geopandas": {"version": "1.0.1", "status": "installed"},
    "shapely": {"version": "2.1.0", "status": "installed"}
  },
  "services": {
    "config": {"status": "up"},
    "gemini_api": {"status": "up", "latency_ms": 120, "model": "gemini-1.5-pro"}
  }
}
```

#### Liveness Probe

**Endpoint:** `GET /health/live`

Kubernetes liveness probe endpoint.

**Response:**
```json
{
  "status": "alive",
  "timestamp": 1686840000
}
```

#### Readiness Probe

**Endpoint:** `GET /health/ready`

Kubernetes readiness probe endpoint.

**Response:**
```json
{
  "status": "ready",
  "timestamp": 1686840000
}
```

#### Diagnostics

**Endpoint:** `GET /diagnostics`

Detailed diagnostic information (non-production only).

**Response:**
```json
{
  "status": "healthy",
  "system": {
    "memory_usage_mb": 156.42,
    "cpu_percent": 2.3,
    "thread_count": 8,
    "open_files": 12
  },
  "environment_details": {
    // Environment variables (sensitive data filtered)
  },
  // All health data
}
```

## Available Tool Categories

### Spatial Query Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `get_location_info` | Get information about a specific location | `location`, `info_types` |
| `calculate_distance` | Calculate distance between two locations | `location1`, `location2`, `unit` |
| `find_nearby_features` | Find features near a location | `location`, `feature_type`, `radius`, `limit` |
| `analyze_area` | Analyze an area for various characteristics | `area`, `analysis_type`, `parameters` |

### Weather Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `get_current_weather` | Get current weather for a location | `location` |
| `get_weather_forecast` | Get weather forecast for a location | `location`, `days` |

### Sustainability Assessment Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `calculate_carbon_footprint` | Calculate carbon footprint | `activity_data`, `activity_type` |
| `analyze_land_use` | Analyze land use patterns | `area`, `timeframe` |
| `assess_water_resources` | Assess water resources in a region | `region`, `parameters` |

### Visualization Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `create_map` | Create an interactive map visualization | `data`, `map_type`, `style_options` |
| `generate_chart` | Generate charts from data | `data`, `chart_type`, `options` |

### Climate Analysis Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `analyze_climate_trends` | Analyze climate trends for a region | `region`, `timeframe`, `variables` |
| `assess_climate_risks` | Assess climate-related risks | `location`, `risk_types`, `horizon` |

### Resilience Planning Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `identify_vulnerabilities` | Identify vulnerabilities in an area | `area`, `hazard_types` |
| `recommend_mitigation_strategies` | Recommend mitigation strategies | `vulnerabilities`, `context` |

## Integration Examples

### JavaScript WebSocket Example

```javascript
// Function to connect to the GIS Agent WebSocket API
function connectToGISAgent(serverUrl) {
  // Create a new WebSocket connection
  const socket = new WebSocket(`ws://${serverUrl}/ws`);
  let sessionId = null;

  // Connection opened
  socket.onopen = (event) => {
    console.log('Connected to GIS Agent WebSocket API');
  };

  // Listen for messages
  socket.onmessage = (event) => {
    const response = JSON.parse(event.data);
    console.log('Received:', response);
    
    // Handle different response types
    if (response.type === 'session_info') {
      // Store session ID
      sessionId = response.session_id;
      console.log(`Session established: ${sessionId}`);
      
      // You can now send queries using this session ID
      // Example: sendQuery('What is the population of Tokyo?');
    } 
    else if (response.type === 'response') {
      // Display AI response to the user
      displayAIResponse(response.content);
    } 
    else if (response.type === 'tool_result') {
      // Handle tool result (e.g., display map or chart)
      handleToolResult(response.tool_name, response.result, response.analysis);
    }
    else if (response.type === 'error') {
      // Display error message
      displayError(response.error);
    }
  };

  // Connection closed
  socket.onclose = (event) => {
    console.log('Disconnected from GIS Agent WebSocket API');
  };

  // Connection error
  socket.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  // Function to send a query
  function sendQuery(queryText) {
    if (socket.readyState === WebSocket.OPEN && sessionId) {
      const message = {
        type: 'query',
        session_id: sessionId,
        query: queryText
      };
      socket.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not ready or session not established');
    }
  }

  // Function to directly call a tool
  function callTool(toolName, arguments) {
    if (socket.readyState === WebSocket.OPEN && sessionId) {
      const message = {
        type: 'tool_call',
        session_id: sessionId,
        tool_name: toolName,
        arguments: arguments
      };
      socket.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not ready or session not established');
    }
  }

  // Function to clear chat history
  function clearHistory() {
    if (socket.readyState === WebSocket.OPEN && sessionId) {
      const message = {
        type: 'clear_history',
        session_id: sessionId
      };
      socket.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not ready or session not established');
    }
  }

  // Return functions for interacting with the API
  return {
    sendQuery,
    callTool,
    clearHistory,
    disconnect: () => socket.close()
  };
}

// Example implementation of response handlers
function displayAIResponse(content) {
  const responseElement = document.getElementById('ai-response');
  responseElement.textContent = content;
}

function handleToolResult(toolName, result, analysis) {
  const resultElement = document.getElementById('tool-result');
  
  // Display AI analysis
  const analysisElement = document.getElementById('result-analysis');
  analysisElement.textContent = analysis;
  
  // Handle different tool results
  if (toolName === 'create_map') {
    // Initialize a map with the result data
    // For example, using Leaflet or similar mapping library
    const mapElement = document.getElementById('map-container');
    // Initialize map with result.center and add features from result.features
    // Example with Leaflet (you would need to include Leaflet in your project)
    // const map = L.map(mapElement).setView([result.center.latitude, result.center.longitude], result.zoom_level);
    // L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
  } 
  else if (toolName === 'generate_chart') {
    // Initialize a chart with the result data
    // For example, using Chart.js or similar charting library
    const chartElement = document.getElementById('chart-container');
    // Create chart with result.data and result.options
  }
  else {
    // For other tools, display JSON result
    resultElement.textContent = JSON.stringify(result, null, 2);
  }
}

function displayError(errorMessage) {
  const errorElement = document.getElementById('error-message');
  errorElement.textContent = errorMessage;
  errorElement.style.display = 'block';
}

// Example usage:
// const gisAgent = connectToGISAgent('your-server-host:port');
// 
// // Send a query when user submits the form
// document.getElementById('query-form').addEventListener('submit', (event) => {
//   event.preventDefault();
//   const queryInput = document.getElementById('query-input');
//   const query = queryInput.value;
//   gisAgent.sendQuery(query);
//   queryInput.value = '';
// });
```

### React Integration Example

```jsx
import React, { useState, useEffect, useRef } from 'react';

// GIS Agent WebSocket Hook
function useGISAgent(serverUrl) {
  const [sessionId, setSessionId] = useState(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    const socket = new WebSocket(`ws://${serverUrl}/ws`);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('Connected to GIS Agent');
      setConnected(true);
    };

    socket.onmessage = (event) => {
      const response = JSON.parse(event.data);
      
      if (response.type === 'session_info') {
        setSessionId(response.session_id);
      } else {
        setMessages((prevMessages) => [...prevMessages, response]);
        setLoading(false);
      }
    };

    socket.onclose = () => {
      console.log('Disconnected from GIS Agent');
      setConnected(false);
      setSessionId(null);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };

    // Clean up on unmount
    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [serverUrl]);

  // Function to send a query
  const sendQuery = (queryText) => {
    if (socketRef.current?.readyState === WebSocket.OPEN && sessionId) {
      const message = {
        type: 'query',
        session_id: sessionId,
        query: queryText
      };
      
      // Add user message to state
      setMessages((prevMessages) => [
        ...prevMessages, 
        { type: 'user_message', content: queryText }
      ]);
      
      setLoading(true);
      socketRef.current.send(JSON.stringify(message));
    }
  };

  // Function to directly call a tool
  const callTool = (toolName, args) => {
    if (socketRef.current?.readyState === WebSocket.OPEN && sessionId) {
      const message = {
        type: 'tool_call',
        session_id: sessionId,
        tool_name: toolName,
        arguments: args
      };
      
      setLoading(true);
      socketRef.current.send(JSON.stringify(message));
    }
  };

  // Function to clear history
  const clearHistory = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN && sessionId) {
      const message = {
        type: 'clear_history',
        session_id: sessionId
      };
      socketRef.current.send(JSON.stringify(message));
      setMessages([]);
    }
  };

  return {
    connected,
    sessionId,
    messages,
    loading,
    sendQuery,
    callTool,
    clearHistory
  };
}

// Example GIS Agent Chat Component
function GISAgentChat({ serverUrl }) {
  const [query, setQuery] = useState('');
  const {
    connected,
    sessionId,
    messages,
    loading,
    sendQuery,
    clearHistory
  } = useGISAgent(serverUrl);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      sendQuery(query);
      setQuery('');
    }
  };

  return (
    <div className="gis-agent-chat">
      <div className="chat-header">
        <h2>GIS Agent Chat</h2>
        <div className="connection-status">
          Status: {connected ? 'Connected' : 'Disconnected'}
          {sessionId && <span> (Session: {sessionId.substring(0, 8)}...)</span>}
        </div>
        <button onClick={clearHistory} disabled={!connected}>Clear History</button>
      </div>
      
      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.type}`}>
            {msg.type === 'user_message' && (
              <div className="user-message">{msg.content}</div>
            )}
            
            {msg.type === 'response' && (
              <div className="ai-response">{msg.content}</div>
            )}
            
            {msg.type === 'tool_result' && (
              <div className="tool-result">
                <h4>Tool Result: {msg.tool_name}</h4>
                {msg.tool_name === 'create_map' ? (
                  <div className="map-container" id={`map-${index}`}>
                    {/* Map would be initialized here using appropriate library */}
                    <p>Map visualization would appear here</p>
                  </div>
                ) : (
                  <pre>{JSON.stringify(msg.result, null, 2)}</pre>
                )}
                {msg.analysis && <div className="result-analysis">{msg.analysis}</div>}
              </div>
            )}
            
            {msg.type === 'error' && (
              <div className="error-message">{msg.error}</div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="loading-indicator">
            <span>Processing your request...</span>
          </div>
        )}
      </div>
      
      <form onSubmit={handleSubmit} className="query-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask the GIS Agent a question..."
          disabled={!connected || loading}
          className="query-input"
        />
        <button type="submit" disabled={!connected || loading || !query.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

export default GISAgentChat;
```

This documentation provides the information you need to integrate the GIS Agent API into your frontend application. Adapt the provided examples to your specific UI framework and requirements. 