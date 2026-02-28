import logging
import os
import re
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, List, Optional, Tuple

from src.models.schemas import AnalysisRequest, ApiResponse, AnalysisResult
from src.services.earth_engine_service import get_ee_status, run_ee_operation
from src.services.genai_service import generate_text

# Import the legacy functions until they are fully refactored
# These will be replaced with proper service calls
from ee_utils import get_tile_url as legacy_get_tile_url, get_admin_boundary

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Helper function to check services
async def check_services():
    """Check if required services are available"""
    errors = []
    ee_status = get_ee_status()
    
    if not ee_status["initialized"]:
        errors.append(f"Earth Engine unavailable: {ee_status['error']}")
    
    if not os.environ.get("EE_PROJECT_ID"):
        errors.append("EE Project ID not configured in .env or environment.")
    
    return errors

# New implementation of analyze_prompt - Previously imported from app.py
async def analyze_user_prompt(prompt: str) -> Optional[AnalysisResult]:
    """
    Analyzes a user prompt to extract parameters for Earth Engine analysis.
    
    Args:
        prompt: The natural language prompt to analyze
        
    Returns:
        AnalysisResult or None if parsing failed
    """
    try:
        logger.info(f"Analyzing prompt: {prompt}")
        
        # For debugging, create a simple hardcoded result if GenAI is not available
        debug_mode = os.environ.get('DEBUG_MODE', '').lower() == 'true'
        if debug_mode:
            logger.info("Using debug mode with hardcoded result")
            # Return a simple hardcoded result for "Show NDVI in Paris"
            return AnalysisResult(
                location="Paris", 
                processing_type="NDVI",
                satellite=None,
                start_date=None,
                end_date=None,
                year="latest",
                latitude=48.8566,
                longitude=2.3522
            )
        
        # Generate a structured analysis using GenAI
        analysis_prompt = f"""Analyze the geographical request: '{prompt}'

Extract the following parameters:
1.  **Location:** City and country (e.g., "Paris, France"). If ambiguous, state the ambiguity.
2.  **Processing Type:** Choose ONE from: RGB, NDVI, Surface WATER, LULC, LST, OPEN BUILDINGS,TREE_COVER, FOREST_LOSS, FOREST_GAIN.
    - Use 'RGB' for general satellite views, true color, visual imagery.
    - Use 'NDVI' for vegetation health, greenery.
    - Use 'Surface WATER' for water body mapping (rivers, lakes).
    - Use 'LULC' for land cover / land use classification.
    - Use 'LST' for land surface temperature, thermal variations, lst etc.
    - Use 'OPEN BUILDINGS' for building footprints or heights.
    - Use "TREE_COVER" for Tree Cover or Forest Cover or Forest in 2000 layer.
    - Use "FOREST_LOSS" for Forest Loss or Tree loss or Deforestation Year layer.
    - Use "FOREST_GAIN" for Forest Gain or Tree Gain layer.
    - Use "SAR" for RADAR imagery, Cloud free imagery or Synthetic Aperture Radar imagery.
    - Use "FLOOD MAPPING" specifically for flood detection, flood extent, inundation mapping, especially if SAR or RADAR is mentioned in the context of flooding.
    - Use "ACTIVE_FIRE" for visualizing recent fire activity, active fire detection, thermal hotspots, wildfire intensity (typically uses FIRMS data)
    - Use "CO" for Carbon Monoxide concentration.
    - Use "NO2" for Nitrogen Dioxide concentration.
    - Use "CH4" for Methane concentration.
    - Use "SO2" for Sulfur Dioxide concentration.
    - If prompt contains “tree cover" use "TREE_COVER".
    - If prompt contains “forest loss" use "FOREST_LOSS".
    - If prompt contains “forest gain" use "FOREST_GAIN".
    - If unsure, default to 'RGB'.
3.  **Satellite (for RGB only):** Specify 'Sentinel-2' or 'Landsat 8' if mentioned. Default to 'Sentinel-2' if RGB is chosen and no satellite specified. Otherwise, output 'None'.
4.  **Start Date:** Extract and return in format (YYYY-MM-DD). Apply the following rules:
    - If both start and end dates are clearly provided, return both in (YYYY-MM-DD) format.
    - If only a **year** is given → Start: YYYY-01-01. End: one year from start.
    - If **month + year** → Start: YYYY-MM-01. End: two months from start.
    - If **season** is mentioned → Use:
        - Spring = YYYY-03-01  
        - Summer = YYYY-06-01  
        - Fall/Autumn = YYYY-09-01  
        - Winter = YYYY-12-01  
        → End date = +2 months
    - If range like “July 2023 to Oct 2023” is mentioned → convert both to full (YYYY-MM-DD).
    - If keywords like "latest", "updated", or "most recent" → Start: 2025-01-01, End: 2025-12-12.
    - If unclear, missing, or ambiguous → Start: 2024-01-01, End: 2024-12-30.

5.  **End Date:** Follows from above logic:
    - If not explicitly given, infer from start date.
    - If start is a full year → End = start + 1 year.
    - If start includes month → End = start + 2 months.
    - If season → End = start + 2 months.
    - If keywords like “latest”, “updated” → use End: 2025-12-12.
    - If unclear or missing → End: 2024-12-30.

6.  **Year (primarily for LST):**
    - If LST is chosen, extract the year (YYYY).
    - If no year given but LST is requested, use year from Start Date.
    - For other types, output year only if clearly mentioned for composite or multi-temporal analysis.


        Format your response as a JSON object with these fields:
        {{
          "location": "string", 
          "processing_type": "string",
          "satellite": "Sentinel-2 or Landsat 8 or None",
          "start_date": "YYYY-MM-DD ",
          "end_date": "YYYY-MM-DD",
        }}
        """
        
        # Call GenAI service to analyze the prompt
        logger.info("Calling GenAI service to analyze prompt")
        response = await generate_text(analysis_prompt)
        if not response:
            logger.error("Failed to get response from GenAI service")
            return None
        
        logger.info(f"GenAI response: {response}")
        
        # Try to parse as JSON first
        result_dict = None
        
        # Check for JSON in the response (enclosed in curly braces)
        json_match = re.search(r'({.*?})', response.replace('\n', ' '), re.DOTALL)
        if json_match:
            # Try to parse the JSON
            try:
                json_str = json_match.group(1)
                logger.info(f"Extracted JSON: {json_str}")
                result_dict = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}, Response: {json_match.group(1)}")
                # Continue to key-value parsing
        
        # If JSON parsing failed, try parsing as key-value pairs
        if not result_dict:
            logger.info("Attempting to parse response as key-value pairs")
            result_dict = {}
            
            # Common field mappings
            field_mappings = {
                'location': ['location'],
                'processing_type': ['processing', 'processing type', 'processing_type', 'type'],
                'satellite': ['satellite'],
                'start_date': ['start date', 'start_date', 'start'],
                'end_date': ['end date', 'end_date', 'end'],
                'year': ['year'],
                'latitude': ['latitude', 'lat'],
                'longitude': ['longitude', 'long', 'lon']
            }
            
            # Parse each line as a potential key-value pair
            lines = response.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    # Skip empty values
                    if not value or value.lower() in ['null', 'none', 'n/a']:
                        continue
                        
                    # Map the key to a standard field name
                    for field, aliases in field_mappings.items():
                        if key in aliases:
                            result_dict[field] = value
                            break
            
            # Check if we extracted enough information
            if not result_dict or 'location' not in result_dict or 'processing_type' not in result_dict:
                logger.error(f"Failed to extract required fields from key-value parsing: {result_dict}")
                
                # As a last resort, try a more aggressive pattern matching
                if 'location' not in result_dict:
                    location_match = re.search(r'location:?\s*([^,\n]+)', response, re.IGNORECASE)
                    if location_match:
                        result_dict['location'] = location_match.group(1).strip()
                
                if 'processing_type' not in result_dict:
                    proc_match = re.search(r'(processing|type):?\s*([^,\n]+)', response, re.IGNORECASE)
                    if proc_match:
                        result_dict['processing_type'] = proc_match.group(2).strip()
        
        # Ensure we have the minimum required fields
        if not result_dict or 'location' not in result_dict or 'processing_type' not in result_dict:
            logger.error(f"Failed to extract required fields from response: {response}")
            return None
            
        # Normalize the fields
        # Convert processing_type to uppercase for consistency
        if result_dict.get('processing_type'):
            result_dict['processing_type'] = result_dict['processing_type'].upper()
            
            # Validate processing_type is one of the supported types
            valid_types = [
                'RGB', 'NDVI', 'WATER', 'SURFACE WATER', 'LULC', 'LST', 'BUILDINGS', 'OPEN BUILDINGS',
                'TREE_COVER', 'FOREST', 'SAR', 'FLOOD MAPPING', 'FOREST_LOSS', 'FOREST_GAIN', 
                'ACTIVE_FIRE', 'FIRE', 'BURNED AREAS', 'BURN SEVERITY',
                'CO', 'NO2', 'CH4', 'SO2'  # Gas types
            ]
            
            # Common aliases that should be mapped in the backend
            processing_type_mapping = {
                'WATER': 'SURFACE WATER',
                'BUILDINGS': 'OPEN BUILDINGS',
                'FOREST': 'TREE_COVER',
                'FIRE': 'ACTIVE_FIRE',
                'BURNED AREAS': 'ACTIVE_FIRE',
                'BURN SEVERITY': 'ACTIVE_FIRE'
            }
            
            # Apply mapping if it exists
            if result_dict['processing_type'] in processing_type_mapping:
                mapped_type = processing_type_mapping[result_dict['processing_type']]
                logger.info(f"Mapping processing type from {result_dict['processing_type']} to {mapped_type}")
                result_dict['processing_type'] = mapped_type
            
            if result_dict['processing_type'] not in valid_types:
                logger.warning(f"Invalid processing type: {result_dict['processing_type']}, defaulting to RGB")
                result_dict['processing_type'] = 'RGB'
        
        # Convert year to int if it's a number
        if result_dict.get("year") and result_dict["year"] != "latest" and result_dict["year"] is not None:
            try:
                result_dict["year"] = int(result_dict["year"])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert year to int: {result_dict['year']}")
        
        # Convert coordinates to float if present
        if result_dict.get("latitude") is not None:
            try:
                result_dict["latitude"] = float(result_dict["latitude"])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert latitude to float: {result_dict['latitude']}")
                result_dict["latitude"] = None
                
        if result_dict.get("longitude") is not None:
            try:
                result_dict["longitude"] = float(result_dict["longitude"])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert longitude to float: {result_dict['longitude']}")
                result_dict["longitude"] = None
        
        # Create and return the AnalysisResult
        logger.info(f"Creating AnalysisResult with: {result_dict}")
        return AnalysisResult(**result_dict)
    
    except Exception as e:
        logger.exception(f"Error analyzing prompt: {e}")
        return None

@router.options("/analyze")
async def options_analyze():
    """Handle OPTIONS requests for the /api/analyze endpoint."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

@router.post("/analyze", response_model=ApiResponse)
async def analyze_prompt(request: AnalysisRequest) -> ApiResponse:
    """
    API endpoint to analyze a prompt and generate Earth Engine visualization.
    
    Args:
        request: The analysis request with prompt and other parameters
        
    Returns:
        API response with results
    """
    # Check if services are available
    if errors := await check_services():
        msg = " ".join(errors)
        if not os.environ.get("EE_PROJECT_ID"):
            msg = f"Configuration Error: EE_PROJECT_ID not set. {msg}"
        return ApiResponse(success=False, message=msg)
    
    try:
        # Use the local implementation instead of importing from app.py
        analysis_result = await analyze_user_prompt(request.prompt)
        if not analysis_result:
            return ApiResponse(success=False, message="Failed to analyze prompt.")
        
        # Convert to dict for further processing
        data = analysis_result.dict()
        
        # Get tile URL and metadata using the legacy function
        # This will be replaced with a proper service call in future
        project_id = os.environ.get("EE_PROJECT_ID")
        tile_url, metadata = await legacy_get_tile_url(
            location=data["location"],
            processing_type=data["processing_type"],
            project_id=project_id,
            satellite=data.get("satellite"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            year=data.get("year"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            llm=None,  # No longer using Ollama
            LLM_INITIALIZED=True  # Assuming GenAI is initialized
        )
        
        # Add results to the data
        data["tile_url"] = tile_url
        data["metadata"] = metadata
        
        # Handle different result cases
        if tile_url is None and metadata and "fail" in metadata.get("Status", "").lower():
            # URL failed but metadata indicates why
            return ApiResponse(success=False, message=f"Error fetching map image: {metadata['Status']}", data=data)
        elif tile_url is None and metadata:
            # URL failed but metadata exists (partial success)
            return ApiResponse(success=True, message="Analysis complete, but map tile generation failed. Metadata available.", data=data)
        elif tile_url is None and not metadata:
            # Complete failure
            return ApiResponse(success=False, message="Error fetching map image and metadata.", data=data)
        
        # Success case
        return ApiResponse(success=True, message="Analysis complete", data=data)
    
    except Exception as e:
        logger.exception("Error in /api/analyze")
        return ApiResponse(success=False, message=f"Unexpected Error: {str(e)}", data={"prompt": request.prompt}) 