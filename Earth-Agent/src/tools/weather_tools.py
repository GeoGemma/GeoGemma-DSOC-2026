"""
Weather tools for the GIS AI Agent.

This module provides tools for retrieving and analyzing weather data,
such as current conditions, forecasts, and historical weather patterns.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
import asyncio

from ..config import get_config
from ..data_sources.openweathermap_connector import get_openweathermap_client

# Configure logging
logger = logging.getLogger(__name__)


async def get_current_weather(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current weather for a location.

    Args:
        arguments: Dictionary containing:
            - location: Location name or coordinates.
            - units: Units of measurement (metric, imperial, standard).

    Returns:
        Dictionary with current weather data.
    """
    location = arguments.get("location", "")
    units = arguments.get("units", "metric")
    
    if not location:
        return {"error": "No location provided"}
    
    try:
        # Get the OpenWeatherMap client
        owm_client = get_openweathermap_client()
        
        # Get weather data
        result = await owm_client.get_current_weather(location, units)
        
        return {"result": result}
    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        return {"error": str(e)}


async def get_weather_forecast(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get weather forecast for a location.

    Args:
        arguments: Dictionary containing:
            - location: Location name or coordinates.
            - days: Number of days for forecast.
            - units: Units of measurement (metric, imperial, standard).

    Returns:
        Dictionary with forecast data.
    """
    location = arguments.get("location", "")
    days = arguments.get("days", 5)
    units = arguments.get("units", "metric")
    
    if not location:
        return {"error": "No location provided"}
    
    if days > 5:
        return {"error": "Maximum forecast days is 5"}
    
    try:
        # Get the OpenWeatherMap client
        owm_client = get_openweathermap_client()
        
        # Get forecast data
        result = await owm_client.get_forecast(location, days, units)
        
        return {"result": result}
    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}")
        return {"error": str(e)}


async def get_air_quality(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get air quality data for a location.

    Args:
        arguments: Dictionary containing:
            - location: Location name or coordinates.

    Returns:
        Dictionary with air quality data.
    """
    location = arguments.get("location", "")
    
    if not location:
        return {"error": "No location provided"}
    
    try:
        # Get the OpenWeatherMap client
        owm_client = get_openweathermap_client()
        
        # Get air quality data
        result = await owm_client.get_air_pollution(location)
        
        return {"result": result}
    except Exception as e:
        logger.error(f"Error getting air quality data: {e}")
        return {"error": str(e)}


# Function to return all weather tools
def weather_tools() -> Dict[str, Dict[str, Any]]:
    """
    Get all weather tools.

    Returns:
        Dictionary of weather tools.
    """
    return {
        "get_current_weather": {
            "function": get_current_weather,
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
        
        "get_weather_forecast": {
            "function": get_weather_forecast,
            "description": "Get weather forecast for a location for up to 5 days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name or coordinates (latitude,longitude)"
                    },
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Number of days for forecast (max 5)"
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
        
        "get_air_quality": {
            "function": get_air_quality,
            "description": "Get air quality data for a specific location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name or coordinates (latitude,longitude)"
                    }
                },
                "required": ["location"]
            }
        }
    } 