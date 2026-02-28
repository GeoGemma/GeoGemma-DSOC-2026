#!/usr/bin/env python3
"""
Basic example of querying the GIS AI Agent.

This script demonstrates how to make a simple query to the GIS AI Agent
using the MCP Server client API.
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

# Add the parent directory to the path to allow importing from the src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gemini.client import get_gemini_client


async def run_query(query, host="localhost", port=8080):
    """
    Run a query against the GIS AI Agent.

    Args:
        query: The natural language query to send to the GIS AI Agent.
        host: The hostname of the GIS AI Agent server.
        port: The port of the GIS AI Agent server.
    
    Returns:
        The response from the GIS AI Agent.
    """
    print(f"Connecting to GIS AI Agent at {host}:{port}")
    print(f"Sending query: {query}")
    
    # Get the Gemini client
    gemini_client = get_gemini_client()
    
    # Create a prompt that instructs the model to use GIS tools
    prompt = f"""
    You are a helpful assistant with expertise in GIS and sustainability. 
    Use the available tools to answer the user's question. 
    Make sure to provide a comprehensive answer with relevant data.
    
    User query: {query}
    """
    
    # Generate text using the Gemini model
    response = await gemini_client.generate_text(prompt)
    
    # Process and print the response
    text_response = response.get("text", "")
    tool_calls = response.get("tool_calls", [])
    
    # If there are tool calls, execute them
    if tool_calls:
        print("\nTools called:")
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("arguments", {})
            
            print(f"  - {tool_name}: {json.dumps(arguments, indent=2)}")
    
    return {
        "query": query,
        "text_response": text_response,
        "tool_calls": tool_calls
    }


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Example GIS AI Agent query")
    
    parser.add_argument(
        "--query",
        default="What is the current water stress level in California?",
        help="Natural language query to send to the GIS AI Agent"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Hostname of the GIS AI Agent server"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port of the GIS AI Agent server"
    )
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()
    
    try:
        # Run the query
        result = await run_query(args.query, args.host, args.port)
        
        # Print the text response
        print("\nResponse:")
        print(result["text_response"])
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 