#!/usr/bin/env python3
"""
Map visualization example for the GIS AI Agent.

This script demonstrates how to use the GIS AI Agent to generate
maps and visualizations for geographic areas.
"""

import sys
import json
import base64
import asyncio
import argparse
from pathlib import Path
import os
import tempfile

# Add the parent directory to the path to allow importing from the src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.visualization import generate_map, create_chart, create_comparison_visualization


async def create_visualization(area, visualization_type="map", output_format="html"):
    """
    Create a visualization for a specific area.

    Args:
        area: The area to visualize (name or coordinates).
        visualization_type: The type of visualization to create:
            - map: Basic map with various layers
            - chart: Chart or graph of data
            - comparison: Comparison visualization
        output_format: Output format (html, png, jpg)

    Returns:
        Path to the generated visualization file.
    """
    print(f"Creating {visualization_type} visualization for {area} in {output_format} format")
    
    if visualization_type == "map":
        # Use the visualization tools for map generation
        result = await generate_map({
            "area": area,
            "layers": ["terrain", "streets"],
            "style": "standard",
            "output_format": output_format
        })
        
        if "error" in result:
            raise ValueError(result["error"])
        
        return result["file_path"]
    
    elif visualization_type == "chart":
        # Use the visualization tools for chart creation
        result = await create_chart({
            "chart_type": "bar",
            "data_source": "temperature_data",
            "parameters": {
                "area": area,
                "time_period": "annual"
            },
            "output_format": output_format
        })
        
        if "error" in result:
            raise ValueError(result["error"])
        
        return result["file_path"]
    
    elif visualization_type == "comparison":
        # Use the visualization tools for comparison visualization
        result = await create_comparison_visualization({
            "comparison_type": "bar",
            "subject1": "2000",
            "subject2": "2023",
            "data_type": "land_cover",
            "parameters": {
                "area": area
            },
            "output_format": output_format
        })
        
        if "error" in result:
            raise ValueError(result["error"])
        
        return result["file_path"]
    
    else:
        raise ValueError(f"Unknown visualization type: {visualization_type}")


def print_image_info(image_path, format):
    """Print information about the generated image."""
    if not os.path.exists(image_path):
        print(f"Warning: File not found at {image_path}")
        return
        
    if format in ["png", "jpg", "jpeg"]:
        print(f"Image saved to: {image_path}")
        print(f"To view the image, open the file in an image viewer.")
    elif format == "html":
        print(f"Interactive map saved to: {image_path}")
        print(f"To view the map, open the HTML file in a web browser.")
    else:
        print(f"Visualization saved to: {image_path}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Map visualization example")
    
    parser.add_argument(
        "--area",
        default="New York City",
        help="Area to visualize (name or coordinates)"
    )
    
    parser.add_argument(
        "--type",
        choices=["map", "chart", "comparison"],
        default="map",
        help="Type of visualization to create"
    )
    
    parser.add_argument(
        "--format",
        choices=["html", "png", "jpg"],
        default="html",
        help="Output format"
    )
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()
    
    try:
        # Create the visualization
        result = await create_visualization(args.area, args.type, args.format)
        
        # Print information about the result
        print("\nVisualization completed.")
        print_image_info(result, args.format)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 