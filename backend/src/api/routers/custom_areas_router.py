import logging
import datetime
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from src.models.schemas import CustomAreaRequest, ApiResponse, CustomAreaData
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/custom-area", response_model=ApiResponse)
async def create_custom_area(request: CustomAreaRequest) -> ApiResponse:
    """
    API endpoint to create a custom area for analysis.
    
    Args:
        request: The custom area request with name, description, and geometry
        
    Returns:
        API response with the created area
    """
    try:
        # Create a simple ID for the custom area
        area_id = f"area_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Log the creation
        logger.info(f"Custom area '{request.name}' defined (ID: {area_id}). Geometry: {request.geometry['type']}")
        
        return ApiResponse(success=True, message="Custom area defined (not saved)", data={
            "id": area_id,
            "name": request.name,
            "description": request.description,
            # "geometry": request.geometry  # Optionally return geometry
        })
    except Exception as e:
        logger.exception("Error creating custom area")
        return ApiResponse(success=False, message=f"Error: {str(e)}")

@router.post("/custom-areas")
async def save_custom_area(data: CustomAreaData) -> Dict[str, str]:
    """
    Save a custom area to Firestore.
    
    Args:
        data: The custom area data to save
        
    Returns:
        Status message
    """
    try:
        firestore_service.save_custom_area(data.user_id, data.area_id, data.area)
        return {"status": "success"}
    except Exception as e:
        logger.exception(f"Error saving custom area: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save custom area: {str(e)}")

@router.get("/custom-areas/{user_id}")
async def get_custom_areas(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all custom areas for a user from Firestore.
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        List of custom areas
    """
    try:
        return firestore_service.get_custom_areas(user_id)
    except Exception as e:
        logger.exception(f"Error getting custom areas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get custom areas: {str(e)}") 