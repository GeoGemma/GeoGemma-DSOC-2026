"""
Visualization tools for the GIS AI Agent.

This module provides tools for creating visualizations of GIS data,
including maps, charts, and interactive visualizations.
"""

import logging
import json
import base64
import io
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
import asyncio

import folium
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from pathlib import Path

from ..config import get_config

# Configure logging
logger = logging.getLogger(__name__)


async def generate_map(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a map visualization of a specific area.

    Args:
        arguments: Dictionary containing:
            - area: Area name or coordinates to center the map on.
            - layers: List of layer names to include.
            - style: Visualization style.
            - output_format: Output format (png, jpg, html).

    Returns:
        Dictionary with the map visualization or link to the visualization file.
    """
    area = arguments.get("area", "")
    layers = arguments.get("layers", [])
    style = arguments.get("style", "standard")
    output_format = arguments.get("output_format", "html")
    
    if not area:
        return {"error": "No area provided"}
    
    try:
        # Simple implementation using folium
        # In a complete implementation, you would integrate with more GIS libraries
        # for advanced features and data layers
        
        # Parse coordinates if provided directly
        if "," in area and all(part.replace(".", "").replace("-", "").isdigit() for part in area.split(",")):
            lat, lon = map(float, area.split(","))
        else:
            # For now, using a placeholder location for non-coordinate inputs
            # In a real implementation, you would geocode this using GeoPy or another service
            logger.warning(f"Area name '{area}' provided; using placeholder coordinates")
            lat, lon = 0, 0
        
        # Create a map
        m = folium.Map(location=[lat, lon], zoom_start=10)
        
        # Add basic layers based on user request
        for layer_name in layers:
            if layer_name == "terrain":
                folium.TileLayer("Stamen Terrain").add_to(m)
            elif layer_name == "satellite":
                # Using CartoDB's Positron as a substitute for satellite imagery
                folium.TileLayer("CartoDB positron").add_to(m)
            elif layer_name == "streets":
                folium.TileLayer("OpenStreetMap").add_to(m)
                
        # Add a marker at the center
        folium.Marker([lat, lon], popup=area).add_to(m)
        
        # Save the map to a file
        temp_dir = Path(tempfile.gettempdir())
        
        if output_format == "html":
            file_path = temp_dir / f"map_{hash(area)}_{hash(str(layers))}.html"
            m.save(str(file_path))
            
            return {
                "file_path": str(file_path),
                "format": "html",
                "area": area,
                "layers": layers
            }
        else:
            # For PNG/JPG, we'd need additional libraries like Selenium to render the HTML
            # This is a placeholder
            return {
                "error": f"Output format {output_format} is not supported in the non-ArcGIS version",
                "suggestion": "Use 'html' as the output format"
            }
    except Exception as e:
        logger.error(f"Error generating map: {e}")
        return {"error": str(e)}


async def create_chart(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a chart visualization of GIS data.

    Args:
        arguments: Dictionary containing:
            - chart_type: Type of chart to create.
            - data_source: Source of the data.
            - parameters: Additional parameters for the chart.
            - output_format: Output format (png, jpg, html).

    Returns:
        Dictionary with the chart visualization or link to the visualization file.
    """
    chart_type = arguments.get("chart_type", "")
    data_source = arguments.get("data_source", "")
    parameters = arguments.get("parameters", {})
    output_format = arguments.get("output_format", "png")
    
    if not chart_type or not data_source:
        return {"error": "Chart type and data source must be provided"}
    
    try:
        # This is a simplified implementation using matplotlib
        # In a real implementation, you would integrate with data sources
        # to get actual data for the chart
        
        # Create a sample dataframe with placeholder data
        np.random.seed(42)  # For reproducibility
        
        if chart_type == "bar":
            # Sample data for a bar chart
            categories = ["Category A", "Category B", "Category C", "Category D", "Category E"]
            values = np.random.randint(1, 100, size=len(categories))
            
            plt.figure(figsize=(10, 6))
            plt.bar(categories, values)
            plt.xlabel("Categories")
            plt.ylabel("Values")
            plt.title(f"Sample Bar Chart: {data_source}")
            
        elif chart_type == "line":
            # Sample data for a line chart
            dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
            values = np.cumsum(np.random.randn(30) * 10)
            
            plt.figure(figsize=(10, 6))
            plt.plot(dates, values)
            plt.xlabel("Date")
            plt.ylabel("Values")
            plt.title(f"Sample Line Chart: {data_source}")
            plt.grid(True)
            
        elif chart_type == "scatter":
            # Sample data for a scatter plot
            x = np.random.randn(50) * 10
            y = np.random.randn(50) * 10
            
            plt.figure(figsize=(10, 6))
            plt.scatter(x, y)
            plt.xlabel("X Values")
            plt.ylabel("Y Values")
            plt.title(f"Sample Scatter Plot: {data_source}")
            plt.grid(True)
            
        elif chart_type == "pie":
            # Sample data for a pie chart
            categories = ["Category A", "Category B", "Category C", "Category D"]
            values = np.random.randint(1, 100, size=len(categories))
            
            plt.figure(figsize=(10, 6))
            plt.pie(values, labels=categories, autopct='%1.1f%%')
            plt.title(f"Sample Pie Chart: {data_source}")
            
        else:
            return {"error": f"Chart type '{chart_type}' is not supported"}
        
        # Save the chart to a file
        temp_dir = Path(tempfile.gettempdir())
        file_path = temp_dir / f"chart_{hash(chart_type)}_{hash(data_source)}.{output_format}"
        
        plt.tight_layout()
        plt.savefig(str(file_path), format=output_format)
        plt.close()
        
        return {
            "file_path": str(file_path),
            "format": output_format,
            "chart_type": chart_type,
            "data_source": data_source
        }
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        return {"error": str(e)}


async def create_comparison_visualization(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a visualization comparing two geographical entities.

    Args:
        arguments: Dictionary containing:
            - comparison_type: Type of comparison to make.
            - subject1: First subject to compare.
            - subject2: Second subject to compare.
            - data_type: Type of data to compare.
            - parameters: Additional parameters for the comparison.
            - output_format: Output format (png, jpg, html).

    Returns:
        Dictionary with the comparison visualization or link to the visualization file.
    """
    comparison_type = arguments.get("comparison_type", "")
    subject1 = arguments.get("subject1", "")
    subject2 = arguments.get("subject2", "")
    data_type = arguments.get("data_type", "")
    parameters = arguments.get("parameters", {})
    output_format = arguments.get("output_format", "png")
    
    if not comparison_type or not subject1 or not subject2 or not data_type:
        return {"error": "Comparison type, subjects, and data type must be provided"}
    
    try:
        # This is a simplified implementation using matplotlib
        # In a real implementation, you would integrate with data sources
        # to get actual data for the comparison
        
        if comparison_type == "bar":
            # Sample data for a bar chart comparison
            categories = ["Metric 1", "Metric 2", "Metric 3", "Metric 4"]
            values1 = np.random.randint(1, 100, size=len(categories))
            values2 = np.random.randint(1, 100, size=len(categories))
            
            x = np.arange(len(categories))
            width = 0.35
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(x - width/2, values1, width, label=subject1)
            ax.bar(x + width/2, values2, width, label=subject2)
            
            ax.set_xlabel("Metrics")
            ax.set_ylabel("Values")
            ax.set_title(f"Comparison of {subject1} and {subject2}: {data_type}")
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            ax.legend()
            ax.grid(True, axis='y')
            
        elif comparison_type == "line":
            # Sample data for a line chart comparison
            dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
            values1 = np.cumsum(np.random.randn(30) * 5 + 1)
            values2 = np.cumsum(np.random.randn(30) * 5 + 2)
            
            plt.figure(figsize=(12, 6))
            plt.plot(dates, values1, label=subject1)
            plt.plot(dates, values2, label=subject2)
            plt.xlabel("Date")
            plt.ylabel("Values")
            plt.title(f"Comparison of {subject1} and {subject2}: {data_type}")
            plt.legend()
            plt.grid(True)
            
        else:
            return {"error": f"Comparison type '{comparison_type}' is not supported"}
        
        # Save the comparison visualization to a file
        temp_dir = Path(tempfile.gettempdir())
        file_path = temp_dir / f"comparison_{hash(subject1)}_{hash(subject2)}.{output_format}"
        
        plt.tight_layout()
        plt.savefig(str(file_path), format=output_format)
        plt.close()
        
        return {
            "file_path": str(file_path),
            "format": output_format,
            "comparison_type": comparison_type,
            "subject1": subject1,
            "subject2": subject2,
            "data_type": data_type
        }
    except Exception as e:
        logger.error(f"Error creating comparison visualization: {e}")
        return {"error": str(e)}


# Function to return all visualization tools
def visualization_tools() -> Dict[str, Dict[str, Any]]:
    """
    Get all visualization tools.

    Returns:
        Dictionary of visualization tools.
    """
    return {
        "generate_map": {
            "function": generate_map,
            "description": "Generate a map visualization of a specific area with various layers and styles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "Area name or coordinates (latitude,longitude) to center the map on"
                    },
                    "layers": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["terrain", "satellite", "streets", "topographic", "heatmap"]
                        },
                        "description": "List of layers to include in the map"
                    },
                    "style": {
                        "type": "string",
                        "enum": ["standard", "dark", "light", "satellite", "topographic"],
                        "description": "Visual style of the map"
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["png", "jpg", "html"],
                        "description": "Output format of the visualization"
                    }
                },
                "required": ["area"]
            }
        },
        
        "create_chart": {
            "function": create_chart,
            "description": "Create a chart visualization of GIS data, such as bar charts, line charts, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "scatter", "pie", "heatmap", "choropleth"],
                        "description": "Type of chart to create"
                    },
                    "data_source": {
                        "type": "string",
                        "description": "Source of the data (e.g., earth_engine_temperature, population_data)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Additional parameters for the chart, such as time range, data filters, etc."
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["png", "jpg", "html"],
                        "description": "Output format of the visualization"
                    }
                },
                "required": ["chart_type", "data_source"]
            }
        },
        
        "create_comparison_visualization": {
            "function": create_comparison_visualization,
            "description": "Create a visualization comparing two geographical entities or time periods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comparison_type": {
                        "type": "string",
                        "enum": ["bar", "line", "map", "split"],
                        "description": "Type of comparison visualization to create"
                    },
                    "subject1": {
                        "type": "string",
                        "description": "First subject (location, time period, etc.) to compare"
                    },
                    "subject2": {
                        "type": "string",
                        "description": "Second subject (location, time period, etc.) to compare"
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Type of data to compare (e.g., temperature, population, land use)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Additional parameters for the comparison"
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["png", "jpg", "html"],
                        "description": "Output format of the visualization"
                    }
                },
                "required": ["comparison_type", "subject1", "subject2", "data_type"]
            }
        }
    } 