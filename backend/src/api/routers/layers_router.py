import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any, List

from src.models.schemas import LayerInfo, LayerData
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/layers", response_model=List[LayerInfo])
async def get_layers(request: Request) -> List[LayerInfo]:
    """
    Get layers from the session.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        List of layer information
    """
    layers_data = request.session.get("layers", [])
    
    # Validate data against Pydantic model
    validated_layers = []
    for layer in layers_data:
        try:
            validated_layers.append(LayerInfo(**layer))
        except Exception as e:
            logger.warning(f"Skipping invalid layer data in session: {layer}. Error: {e}")
    
    return validated_layers

@router.delete("/layers/{layer_id}")
async def delete_layer(request: Request, layer_id: str) -> Dict[str, Any]:
    """
    Delete a layer from the session.
    
    Args:
        request: The FastAPI request object
        layer_id: The ID of the layer to delete
        
    Returns:
        Status message
    """
    layers = request.session.get("layers", [])
    initial_length = len(layers)
    updated_layers = [layer for layer in layers if layer.get("id") != layer_id]
    
    if len(updated_layers) < initial_length:
        request.session["layers"] = updated_layers
        logger.info(f"Deleted layer {layer_id} from session.")
        return {"success": True, "message": f"Layer {layer_id} deleted"}
    else:
        logger.warning(f"Attempted to delete non-existent layer ID: {layer_id}")
        return {"success": False, "message": f"Layer {layer_id} not found"}

@router.post("/layers/clear")
async def clear_layers(request: Request) -> Dict[str, Any]:
    """
    Clear all layers from the session.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        Status message
    """
    request.session["layers"] = []
    logger.info("Cleared all layers from session.")
    return {"success": True, "message": "All layers cleared"}

@router.post("/layers")
async def save_map_layer(data: LayerData) -> Dict[str, str]:
    """
    Save a map layer to Firestore.
    
    Args:
        data: The layer data to save
        
    Returns:
        Status message
    """
    try:
        firestore_service.save_map_layer(data.user_id, data.layer_id, data.layer)
        return {"status": "success"}
    except Exception as e:
        logger.exception(f"Error saving map layer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save map layer: {str(e)}")

@router.get("/layers/{user_id}")
async def get_map_layers(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all map layers for a user from Firestore.
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        List of layers
    """
    try:
        return firestore_service.get_map_layers(user_id)
    except Exception as e:
        logger.exception(f"Error getting map layers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get map layers: {str(e)}")

@router.delete("/layers/{user_id}/{layer_id}")
async def delete_user_layer(user_id: str, layer_id: str) -> Dict[str, Any]:
    """
    Delete a layer from Firestore.
    
    Args:
        user_id: The user ID
        layer_id: The layer ID to delete
        
    Returns:
        Status message
    """
    try:
        firestore_service.delete_map_layer(user_id, layer_id)
        return {"status": "success", "message": f"Layer {layer_id} deleted for user {user_id}"}
    except Exception as e:
        logger.exception(f"Error deleting layer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete layer: {str(e)}")

@router.delete("/layers/{user_id}")
async def clear_user_layers(user_id: str) -> Dict[str, Any]:
    """
    Clear all layers for a user from Firestore.
    
    Args:
        user_id: The user ID
        
    Returns:
        Status message
    """
    try:
        firestore_service.clear_user_layers(user_id)
        return {"status": "success", "message": f"All layers cleared for user {user_id}"}
    except Exception as e:
        logger.exception(f"Error clearing layers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear layers: {str(e)}")

@router.get("/saved-layers")
async def get_saved_layers(user_id: str = None, limit: int = 20, skip: int = 0) -> List[Any]:
    """
    Placeholder for getting saved layers.
    This endpoint is for backwards compatibility.
    
    Returns:
        Empty list
    """
    logger.info("Accessed /api/saved-layers (DB removed, returning empty list)")
    return [] 