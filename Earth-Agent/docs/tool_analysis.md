# Tool Result Analysis

This document explains the tool result analysis feature in the GIS Agent, which automatically sends tool results back to the AI model for detailed analysis.

## Overview

The GIS Agent now performs a two-pass process when handling tool calls:

1. First, the appropriate tool is executed to retrieve raw data (e.g., weather information, geographic data)
2. Then, this raw data is sent back to the Gemini model for detailed analysis, insights, and explanations
3. Both the raw data and the AI analysis are sent to the user interface

This creates a more intelligent workflow where the AI can provide contextual understanding and insights about the data returned by tools.

## Key Benefits

- **Deeper Insights**: The AI analyzes patterns, trends, and implications in the data
- **Contextual Understanding**: Raw data is transformed into meaningful explanations
- **User-Friendly Interpretation**: Technical data becomes more accessible through AI analysis
- **Expert Domain Knowledge**: The AI applies its knowledge to interpret domain-specific information
- **Automated Analysis**: Users receive analysis without having to request it separately

## How It Works

1. **Tool Execution**: A tool is called with the appropriate arguments
2. **Data Collection**: The tool returns raw data (e.g., JSON, metrics, etc.)
3. **Analysis Generation**: The raw data is sent to Gemini with a prompt requesting analysis
4. **Context Integration**: The analysis considers the user's original question and conversation history
5. **Dual Response**: The user receives both the raw data and the AI's analysis as separate messages

## Technical Implementation

### Server-Side

- The `_analyze_tool_result` method in the `MCPServer` class handles sending tool results to Gemini
- The analysis request includes specific instructions to focus on key findings, patterns, and insights
- The analysis is performed within the context of the user's conversation history
- Both direct tool calls and AI-initiated tool calls use the analysis feature

### Client-Side

- The frontend displays both the raw data and the analysis as separate messages
- A brief typing animation separates the data from the analysis for better user experience
- The raw data is formatted in a JSON code block for technical users
- The analysis is presented in natural language for accessibility

## Example Analysis Focus

The AI is instructed to focus on:

1. Key findings and patterns in the data
2. Noteworthy observations
3. Contextual information to help understand the results
4. Potential implications or recommendations based on the data

## Future Improvements

- Allow users to toggle automatic analysis on/off
- Provide different types of analysis (brief summary vs. detailed analysis)
- Support specialized analysis for different data types (time series, geographic, etc.)
- Enable follow-up questions specifically about the analysis
- Integrate visualization suggestions based on the data type 

## Gemini Fallback for Unavailable Tools

The GIS Agent now provides a seamless experience when a specific tool or data source is not available to answer a user's query. Instead of showing "no tool found" or "no data available" errors, the system automatically uses Gemini's powerful AI model to provide relevant analysis.

### Key Benefits

- **No Dead Ends**: Users never encounter "I don't know" or "no tool available" responses
- **Continuous Assistance**: Every query receives a thoughtful, informative response
- **Knowledge Utilization**: Leverages Gemini's extensive knowledge of GIS, climate science, and environmental data
- **Transparent Fallback**: Clearly indicates when providing a general AI response vs. tool-specific data

### How It Works

1. **Tool Unavailability Detection**: The system detects when:
   - No appropriate tool exists for a query
   - A tool call fails to produce results
   - The AI response contains generic "I don't know" language

2. **Gemini Fallback Activation**: The `analyze_query_with_gemini` function is called with:
   - The original user query
   - Any relevant context from the conversation

3. **Specialized Prompt Construction**: A prompt is created instructing Gemini to:
   - Draw upon its knowledge of geographic systems, climate science, and environmental data
   - Make reasonable estimations when specific data isn't available
   - Clearly indicate when making estimations vs. stating known facts
   - Suggest what specific data would ideally answer the question

4. **Response Delivery**: The AI analysis is delivered to the user with:
   - A clear indication that it's using general AI analysis rather than specific tool data
   - Comprehensive information that addresses the user's query as helpfully as possible

### When Fallback is Used

The fallback activates in three scenarios:

1. **Unknown Tool Request**: When the AI requests a tool that doesn't exist in the system
2. **Generic AI Responses**: When the AI returns phrases like "I don't know" or "I don't have access"
3. **Empty Responses**: When the AI fails to generate a substantive response

### Technical Implementation

- The `analyze_query_with_gemini` function in `src/mcp_server/tools.py` handles the specialized prompt creation
- The server's `_handle_websocket_message` method detects when to activate the fallback
- Fallback responses are clearly labeled in the response message type for frontend handling 