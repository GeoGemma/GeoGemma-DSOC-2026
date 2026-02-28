#!/usr/bin/env python3
"""
Weather data example for the GIS AI Agent.

This script demonstrates how to use the GIS AI Agent to get
weather data and forecasts from OpenWeatherMap.
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

# Add the parent directory to the path to allow importing from the src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_sources.openweathermap_connector import get_openweathermap_client


async def get_weather_data(location, data_type="current", days=5, units="metric"):
    """
    Get weather data for a specific location.

    Args:
        location: Location name or coordinates.
        data_type: Type of data to retrieve (current, forecast, air_quality).
        days: Number of days for forecast (max 5 for free tier).
        units: Units of measurement (metric, imperial, standard).

    Returns:
        Weather data as a dictionary.
    """
    print(f"Getting {data_type} weather data for {location}")
    
    # Get the OpenWeatherMap client
    owm_client = get_openweathermap_client()
    
    if data_type == "current":
        # Get current weather
        result = await owm_client.get_current_weather(location, units)
        
        # Print a summary
        location_name = result.get("location", {}).get("name", "Unknown")
        country = result.get("location", {}).get("country", "")
        temp = result.get("weather", {}).get("temperature", {}).get("current", 0)
        desc = result.get("weather", {}).get("description", "")
        
        print(f"\nCurrent Weather for {location_name}, {country}:")
        print(f"Temperature: {temp}°C")
        print(f"Conditions: {desc}")
        
        return result
    
    elif data_type == "forecast":
        # Get forecast
        result = await owm_client.get_forecast(location, days, units)
        
        # Print a summary
        location_name = result.get("location", {}).get("name", "Unknown")
        country = result.get("location", {}).get("country", "")
        
        print(f"\nWeather Forecast for {location_name}, {country}:")
        
        # Group forecast by day
        forecast_days = {}
        for item in result.get("forecast", []):
            date = item.get("date_time", "").split(" ")[0]
            if date not in forecast_days:
                forecast_days[date] = []
            forecast_days[date].append(item)
        
        # Print summary for each day
        for date, items in forecast_days.items():
            temps = [item.get("temperature", {}).get("value", 0) for item in items]
            avg_temp = sum(temps) / len(temps)
            descriptions = [item.get("weather", {}).get("description", "") for item in items]
            
            print(f"\n{date}:")
            print(f"  Avg. Temperature: {avg_temp:.1f}°C")
            print(f"  Conditions: {', '.join(set(descriptions))}")
        
        return result
    
    elif data_type == "air_quality":
        # Get air quality
        result = await owm_client.get_air_pollution(location)
        
        # Print a summary
        aqi = result.get("air_quality_index", {}).get("value", 0)
        aqi_desc = result.get("air_quality_index", {}).get("description", "Unknown")
        pollutants = result.get("pollutants", {})
        
        print(f"\nAir Quality for {location}:")
        print(f"Air Quality Index: {aqi} - {aqi_desc}")
        print(f"PM2.5: {pollutants.get('pm2_5', {}).get('value', 0)} μg/m³")
        print(f"PM10: {pollutants.get('pm10', {}).get('value', 0)} μg/m³")
        print(f"NO2: {pollutants.get('no2', {}).get('value', 0)} μg/m³")
        print(f"O3: {pollutants.get('o3', {}).get('value', 0)} μg/m³")
        
        return result
    
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Weather data example")
    
    parser.add_argument(
        "--location",
        default="London",
        help="Location to get weather data for (name or coordinates)"
    )
    
    parser.add_argument(
        "--type",
        choices=["current", "forecast", "air_quality"],
        default="current",
        help="Type of weather data to retrieve"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="Number of days for forecast (max 5)"
    )
    
    parser.add_argument(
        "--units",
        choices=["metric", "imperial", "standard"],
        default="metric",
        help="Units of measurement"
    )
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()
    
    try:
        # Get weather data
        result = await get_weather_data(
            args.location,
            args.type,
            args.days,
            args.units
        )
        
        # Save full results to file
        output_file = f"{args.type}_{args.location.replace(' ', '_')}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\nFull results saved to {output_file}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 