import logging
import os
import ee
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, List, Optional

from src.models.schemas import TimeSeriesRequest, ApiResponse
from src.services.earth_engine_service import get_ee_status, run_ee_operation

# Import the legacy functions until they are fully refactored
from ee_utils import process_time_series, get_admin_boundary

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

@router.post("/time-series", response_model=ApiResponse)
async def create_time_series(request: TimeSeriesRequest) -> ApiResponse:
    """
    API endpoint to create a time series analysis.
    
    Args:
        request: The time series request with location, processing type, and date range
        
    Returns:
        API response with time series data
    """
    # Check if services are available
    if errors := await check_services():
        msg = " ".join(errors)
        if not os.environ.get("EE_PROJECT_ID"):
            msg = f"Configuration Error: EE_PROJECT_ID not set. {msg}"
        return ApiResponse(success=False, message=msg)
    
    try:
        # Get admin boundary using the legacy function
        # This will be migrated to the service layer in future
        geometry = await get_admin_boundary(
            request.location, request.start_date, request.end_date,
            None, None, None, True  # Using None for llm, True for LLM_INITIALIZED
        )
        
        if not geometry:
            return ApiResponse(success=False, message=f"Could not find location or geometry for: {request.location}")
        
        # Process time series using the legacy function
        # This will be migrated to the service layer in future
        project_id = os.environ.get("EE_PROJECT_ID")
        time_series_results = process_time_series(
            geometry=geometry,
            processing_type=request.processing_type,
            start_date=request.start_date,
            end_date=request.end_date,
            interval=request.interval,
            project_id=project_id
        )
        
        # Handle errors
        if not time_series_results or (isinstance(time_series_results, list) and time_series_results[0].get("error")):
            error_msg = time_series_results[0].get("error") if time_series_results else "Failed to process time series."
            return ApiResponse(success=False, message=error_msg, data={"request": request.dict()})
        
        # Success case
        return ApiResponse(success=True, message="Time series created successfully", data={
            "location": request.location,
            "processing_type": request.processing_type,
            "interval": request.interval,
            "time_steps": time_series_results  # Contains URL and metadata per step
        })
    
    except ee.EEException as e:
        logger.exception("EE Error creating time series")
        # Include project ID in error message
        return ApiResponse(
            success=False, 
            message=f"Earth Engine Error (Project: {os.environ.get('EE_PROJECT_ID')}): {str(e)}", 
            data={"request": request.dict()}
        )
    except Exception as e:
        logger.exception("Error creating time series")
        return ApiResponse(success=False, message=f"Unexpected Error: {str(e)}", data={"request": request.dict()}) 