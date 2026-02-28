"""
OpenWeatherMap connector for the GIS AI Agent.

This module provides a client for interacting with the OpenWeatherMap API,
allowing the agent to access weather data and forecasts.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
import asyncio
import tempfile
import os
from pathlib import Path
import aiohttp
import time
from ..config import get_config

# Configure logging
logger = logging.getLogger(__name__)


class OpenWeatherMapClient:
    """Client for interacting with the OpenWeatherMap API."""

    def __init__(self):
        """Initialize the OpenWeatherMap client."""
        self.config = get_config()
        self.api_key = None
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self._get_api_key()

    def _get_api_key(self) -> None:
        """Get the OpenWeatherMap API key from configuration or environment."""
        # Try to get from configuration
        owm_config = self.config.get_api_keys().get("openweathermap", {})
        self.api_key = owm_config.get("api_key")
        
        # If not in configuration, try environment variable
        if not self.api_key:
            self.api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
        
        if not self.api_key:
            logger.warning("No OpenWeatherMap API key found. Some features may not work.")

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the OpenWeatherMap API.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            API response data.
        """
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not configured")
        
        # Add API key to parameters
        params["appid"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenWeatherMap API error: {error_text}")
                    raise Exception(f"OpenWeatherMap API error: {response.status} - {error_text}")
                
                return await response.json()

    async def get_current_weather(self, location: str, units: str = "metric") -> Dict[str, Any]:
        """
        Get current weather for a location.

        Args:
            location: Location name or coordinates (lat,lon).
            units: Units of measurement (metric, imperial, standard).

        Returns:
            Current weather data.
        """
        try:
            params = {"units": units}
            
            # Check if location is coordinates
            if "," in location and all(part.replace(".", "").replace("-", "").isdigit() 
                                     for part in location.split(",")):
                lat, lon = map(float, location.split(","))
                params["lat"] = lat
                params["lon"] = lon
            else:
                # Location name
                params["q"] = location
            
            # Make API request
            result = await self._make_request("weather", params)
            
            # Process and return results
            return {
                "location": {
                    "name": result.get("name", ""),
                    "country": result.get("sys", {}).get("country", ""),
                    "coordinates": {
                        "latitude": result.get("coord", {}).get("lat", 0),
                        "longitude": result.get("coord", {}).get("lon", 0)
                    }
                },
                "weather": {
                    "description": result.get("weather", [{}])[0].get("description", ""),
                    "temperature": {
                        "current": result.get("main", {}).get("temp", 0),
                        "feels_like": result.get("main", {}).get("feels_like", 0),
                        "min": result.get("main", {}).get("temp_min", 0),
                        "max": result.get("main", {}).get("temp_max", 0),
                        "unit": "°C" if units == "metric" else "°F" if units == "imperial" else "K"
                    },
                    "humidity": {
                        "value": result.get("main", {}).get("humidity", 0),
                        "unit": "%"
                    },
                    "pressure": {
                        "value": result.get("main", {}).get("pressure", 0),
                        "unit": "hPa"
                    },
                    "wind": {
                        "speed": result.get("wind", {}).get("speed", 0),
                        "direction": result.get("wind", {}).get("deg", 0),
                        "speed_unit": "m/s" if units == "metric" else "mph" if units == "imperial" else "m/s"
                    },
                    "clouds": {
                        "value": result.get("clouds", {}).get("all", 0),
                        "unit": "%"
                    },
                    "timestamp": result.get("dt", 0),
                    "sunrise": result.get("sys", {}).get("sunrise", 0),
                    "sunset": result.get("sys", {}).get("sunset", 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting current weather: {e}")
            raise

    async def get_forecast(self, location: str, days: int = 5, units: str = "metric") -> Dict[str, Any]:
        """
        Get weather forecast for a location.

        Args:
            location: Location name or coordinates (lat,lon).
            days: Number of days for forecast (max 5 for free tier).
            units: Units of measurement (metric, imperial, standard).

        Returns:
            Weather forecast data.
        """
        try:
            params = {"units": units}
            
            # Check if location is coordinates
            if "," in location and all(part.replace(".", "").replace("-", "").isdigit() 
                                     for part in location.split(",")):
                lat, lon = map(float, location.split(","))
                params["lat"] = lat
                params["lon"] = lon
            else:
                # Location name
                params["q"] = location
            
            # Make API request
            result = await self._make_request("forecast", params)
            
            # Process and return results
            forecast_data = []
            for item in result.get("list", []):
                forecast_data.append({
                    "timestamp": item.get("dt", 0),
                    "date_time": item.get("dt_txt", ""),
                    "temperature": {
                        "value": item.get("main", {}).get("temp", 0),
                        "feels_like": item.get("main", {}).get("feels_like", 0),
                        "min": item.get("main", {}).get("temp_min", 0),
                        "max": item.get("main", {}).get("temp_max", 0),
                        "unit": "°C" if units == "metric" else "°F" if units == "imperial" else "K"
                    },
                    "weather": {
                        "description": item.get("weather", [{}])[0].get("description", ""),
                        "icon": item.get("weather", [{}])[0].get("icon", "")
                    },
                    "precipitation": {
                        "probability": item.get("pop", 0) * 100,
                        "unit": "%"
                    },
                    "humidity": {
                        "value": item.get("main", {}).get("humidity", 0),
                        "unit": "%"
                    },
                    "wind": {
                        "speed": item.get("wind", {}).get("speed", 0),
                        "direction": item.get("wind", {}).get("deg", 0),
                        "speed_unit": "m/s" if units == "metric" else "mph" if units == "imperial" else "m/s"
                    }
                })
            
            return {
                "location": {
                    "name": result.get("city", {}).get("name", ""),
                    "country": result.get("city", {}).get("country", ""),
                    "coordinates": {
                        "latitude": result.get("city", {}).get("coord", {}).get("lat", 0),
                        "longitude": result.get("city", {}).get("coord", {}).get("lon", 0)
                    }
                },
                "forecast": forecast_data[:days * 8]  # 8 data points per day (3-hour intervals)
            }
        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            raise

    async def get_air_pollution(self, location: str) -> Dict[str, Any]:
        """
        Get air pollution data for a location.

        Args:
            location: Location coordinates (lat,lon) or name.

        Returns:
            Air pollution data.
        """
        try:
            params = {}
            
            # OpenWeatherMap air pollution API requires coordinates
            if "," in location and all(part.replace(".", "").replace("-", "").isdigit() 
                                     for part in location.split(",")):
                lat, lon = map(float, location.split(","))
                params["lat"] = lat
                params["lon"] = lon
            else:
                # For location names, first get coordinates
                weather_data = await self.get_current_weather(location)
                coords = weather_data.get("location", {}).get("coordinates", {})
                params["lat"] = coords.get("latitude", 0)
                params["lon"] = coords.get("longitude", 0)
            
            # Make API request
            result = await self._make_request("air_pollution", params)
            
            # Process and return results
            pollution_data = result.get("list", [{}])[0]
            components = pollution_data.get("components", {})
            
            return {
                "location": {
                    "coordinates": {
                        "latitude": params.get("lat", 0),
                        "longitude": params.get("lon", 0)
                    }
                },
                "timestamp": pollution_data.get("dt", 0),
                "air_quality_index": {
                    "value": pollution_data.get("main", {}).get("aqi", 0),
                    "description": self._get_aqi_description(pollution_data.get("main", {}).get("aqi", 0))
                },
                "pollutants": {
                    "co": {
                        "value": components.get("co", 0),
                        "unit": "μg/m³"
                    },
                    "no": {
                        "value": components.get("no", 0),
                        "unit": "μg/m³"
                    },
                    "no2": {
                        "value": components.get("no2", 0),
                        "unit": "μg/m³"
                    },
                    "o3": {
                        "value": components.get("o3", 0),
                        "unit": "μg/m³"
                    },
                    "so2": {
                        "value": components.get("so2", 0),
                        "unit": "μg/m³"
                    },
                    "pm2_5": {
                        "value": components.get("pm2_5", 0),
                        "unit": "μg/m³"
                    },
                    "pm10": {
                        "value": components.get("pm10", 0),
                        "unit": "μg/m³"
                    },
                    "nh3": {
                        "value": components.get("nh3", 0),
                        "unit": "μg/m³"
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error getting air pollution data: {e}")
            raise

    def _get_aqi_description(self, aqi: int) -> str:
        """Get description for Air Quality Index value."""
        if aqi == 1:
            return "Good"
        elif aqi == 2:
            return "Fair"
        elif aqi == 3:
            return "Moderate"
        elif aqi == 4:
            return "Poor"
        elif aqi == 5:
            return "Very Poor"
        else:
            return "Unknown"


# Create a singleton instance
openweathermap_client = OpenWeatherMapClient()


def get_openweathermap_client() -> OpenWeatherMapClient:
    """Get the OpenWeatherMap client instance."""
    return openweathermap_client 