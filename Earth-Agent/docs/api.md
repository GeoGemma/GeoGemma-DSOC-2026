# GIS Agent API Reference

This document describes the API endpoints available in the GIS Agent.

## Base URLs

- Local development: `http://localhost:8080`
- API Base Path: `/api`

## Authentication

Currently, the API does not require authentication for local development. Production deployments should implement appropriate authentication mechanisms.

## API Endpoints

### Root Endpoint

```
GET /
```

Returns basic information about the server.

**Example Response:**
```json
{
  "name": "GIS AI Agent",
  "version": "0.2.0",
  "status": "running",
  "tools_count": 16
}
```

### Health Check

```
GET /health
```

Returns the health status of the server.

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": 1715115369.45
}
```

### List Available Tools

```
GET /tools
```

Returns a list of all available tools that can be used by the GIS Agent.

**Example Response:**
```json
{
  "tools": [
    {
      "name": "get_location_info",
      "description": "Get information about a location, such as coordinates, administrative boundaries, and basic geographic features.",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "Location name or address"
          }
        },
        "required": ["location"]
      }
    },
    {
      "name": "get_current_weather",
      "description": "Get current weather conditions for a specific location.",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "Location name or coordinates (latitude,longitude)"
          },
          "units": {
            "type": "string",
            "enum": ["metric", "imperial", "standard"],
            "description": "Units of measurement"
          }
        },
        "required": ["location"]
      }
    },
    // Additional tools...
  ]
}
```

## WebSocket API

### Connect to WebSocket

```
WebSocket /ws
```

Establishes a WebSocket connection for real-time communication with the GIS Agent.

### WebSocket Messages

The WebSocket accepts and returns JSON messages. Each message has a `type` field that determines its purpose.

#### Message Types (Client to Server)

1. **Query Message**:
   ```json
   {
     "type": "query",
     "query": "What's the weather in New York?",
     "session_id": "optional-session-id"
   }
   ```

2. **Direct Tool Call**:
   ```json
   {
     "type": "tool_call",
     "tool_name": "get_current_weather",
     "arguments": {
       "location": "New York",
       "units": "metric"
     },
     "session_id": "optional-session-id"
   }
   ```

3. **Clear History**:
   ```json
   {
     "type": "clear_history",
     "session_id": "optional-session-id"
   }
   ```

#### Message Types (Server to Client)

1. **Session Info**:
   ```json
   {
     "type": "session_info",
     "session_id": "a-unique-session-id"
   }
   ```

2. **Response**:
   ```json
   {
     "type": "response",
     "query": "What's the weather in New York?",
     "response": "The weather in New York is currently cloudy with a temperature of 72°F.",
     "session_id": "session-id"
   }
   ```

3. **Tool Result with Analysis**:
   ```json
   {
     "type": "tool_result_with_analysis",
     "tool_name": "get_current_weather",
     "arguments": {
       "location": "New York",
       "units": "metric"
     },
     "result": {
       "result": {
         "temperature": 22.5,
         "humidity": 65,
         "weather": "cloudy",
         "wind_speed": 12.3
       }
     },
     "analysis": "The current weather in New York is cloudy with a comfortable temperature of 22.5°C (72.5°F). The humidity is moderately high at 65%, which might make it feel a bit warmer. Wind speeds are at 12.3 km/h, providing a light breeze. Overall, it's a typical spring day in New York with comfortable conditions for outdoor activities.",
     "session_id": "session-id"
   }
   ```

4. **Error**:
   ```json
   {
     "error": "No query provided",
     "session_id": "session-id"
   }
   ```

5. **History Cleared**:
   ```json
   {
     "type": "history_cleared",
     "success": true,
     "session_id": "session-id"
   }
   ```

## Rate Limits

The API implements rate limiting to prevent abuse:

- Query messages: 10 requests per minute per session, with a burst allowance of 15
- Tool calls: 20 requests per minute per session, with a burst allowance of 25

## Error Handling

Errors are returned as JSON objects with an `error` field containing a description of the error.

**Example Error Response:**
```json
{
  "error": "Rate limit exceeded. Please try again later.",
  "session_id": "session-id"
}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json` 