#!/usr/bin/env python3
"""
Sustainability assessment example for the GIS AI Agent.

This script demonstrates how to use the GIS AI Agent to perform
a sustainability assessment for a specific area.
"""

import sys
import json
import asyncio
import argparse
import os
from pathlib import Path

# Add the parent directory to the path to allow importing from the src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_sources.earth_engine_connector import get_earth_engine_client
from src.data_sources.openweathermap_connector import get_openweathermap_client


async def assess_sustainability(area, analysis_type="carbon_footprint", service_account_file=None, project_id=None):
    """
    Perform a sustainability assessment for a specific area.

    Args:
        area: The area to assess (name or coordinates).
        analysis_type: The type of sustainability assessment to perform.
            Options: carbon_footprint, water_resources, biodiversity, land_use, risk
        service_account_file: Path to Google Earth Engine service account JSON file.
        project_id: Google Cloud project ID for Earth Engine.

    Returns:
        The assessment results.
    """
    print(f"Performing {analysis_type} assessment for {area}")
    
    # Check if service account file exists
    if service_account_file and not os.path.exists(service_account_file):
        print(f"Warning: Service account file not found at {service_account_file}")
        service_account_file = None
    
    if analysis_type == "carbon_footprint":
        # Use the Earth Engine client for carbon footprint analysis
        client = get_earth_engine_client(service_account_file=service_account_file, project_id=project_id)
        result = await client.calculate_carbon_footprint(
            area=area,
            activity_type="all",
            time_period="annual",
            parameters={}
        )
    
    elif analysis_type == "water_resources":
        # Use the Earth Engine client for water resources analysis
        client = get_earth_engine_client(service_account_file=service_account_file, project_id=project_id)
        result = await client.analyze_water_resources(
            area=area,
            analysis_type="availability",
            time_period="current",
            parameters={}
        )
    
    elif analysis_type == "biodiversity":
        # Use the Earth Engine client for biodiversity assessment
        client = get_earth_engine_client(service_account_file=service_account_file, project_id=project_id)
        result = await client.assess_biodiversity(
            area=area,
            species_type="all",
            parameters={}
        )
    
    elif analysis_type == "land_use":
        # Use the Earth Engine client for land use analysis
        client = get_earth_engine_client(service_account_file=service_account_file, project_id=project_id)
        result = await client.analyze_land_use_change(
            area=area,
            start_year=2000,
            end_year=2023,
            categories=["forest", "urban", "agriculture", "water"]
        )
    
    elif analysis_type == "risk":
        # Use both Earth Engine and OpenWeatherMap for environmental risk assessment
        ee_client = get_earth_engine_client(service_account_file=service_account_file, project_id=project_id)
        owm_client = get_openweathermap_client()
        
        # Get weather data for the area
        weather_data = await owm_client.get_current_weather(area)
        
        # Get environmental risk assessment from Earth Engine
        risk_data = await ee_client.calculate_environmental_risk(
            area=area,
            risk_type="fire",
            time_frame="future_30_years",
            parameters={}
        )
        
        # Combine the results
        result = {
            "risk_assessment": risk_data,
            "current_weather": weather_data
        }
    
    else:
        result = {"error": f"Unknown analysis type: {analysis_type}"}
    
    return result


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Sustainability assessment example")
    
    parser.add_argument(
        "--area",
        default="California",
        help="Area to assess (name or coordinates)"
    )
    
    parser.add_argument(
        "--type",
        choices=["carbon_footprint", "water_resources", "biodiversity", "land_use", "risk"],
        default="carbon_footprint",
        help="Type of sustainability assessment to perform"
    )
    
    parser.add_argument(
        "--service-account-file",
        help="Path to Google Earth Engine service account JSON file"
    )
    
    parser.add_argument(
        "--project-id",
        help="Google Cloud project ID for Earth Engine"
    )
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()
    
    try:
        # Perform the sustainability assessment
        result = await assess_sustainability(
            args.area, 
            args.type,
            service_account_file=args.service_account_file,
            project_id=args.project_id
        )
        
        # Print the results
        print("\nAssessment Results:")
        print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 