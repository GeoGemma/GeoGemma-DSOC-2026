import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from src.models.schemas import UserProfile
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/user-profile")
async def create_user_profile(profile: UserProfile) -> Dict[str, str]:
    """
    Create or update a user profile.
    
    Args:
        profile: The user profile to create or update
        
    Returns:
        Status message
    """
    try:
        firestore_service.create_user_profile(profile.user_id, profile.profile)
        return {"status": "success"}
    except Exception as e:
        logger.exception(f"Error creating user profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user profile: {str(e)}")

@router.get("/user-profile/{user_id}")
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Get a user profile by ID.
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        The user profile
    """
    profile = firestore_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile

@router.patch("/user-profile/{user_id}")
async def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, str]:
    """
    Update a user profile with partial data.
    
    Args:
        user_id: The user ID to update
        updates: The partial update data
        
    Returns:
        Status message
    """
    try:
        firestore_service.update_user_profile(user_id, updates)
        return {"status": "updated"}
    except Exception as e:
        logger.exception(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}") 