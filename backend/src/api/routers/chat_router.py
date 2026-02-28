import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from src.models.schemas import ChatMessage, AnalyticsEvent
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/chat-history")
async def save_chat_message(data: ChatMessage) -> Dict[str, str]:
    """
    Save a chat message to Firestore.
    
    Args:
        data: The chat message data to save
        
    Returns:
        Status message
    """
    try:
        firestore_service.save_chat_message(data.user_id, data.message_id, data.message)
        return {"status": "success"}
    except Exception as e:
        logger.exception(f"Error saving chat message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save chat message: {str(e)}")

@router.get("/chat-history/{user_id}")
async def get_chat_history(user_id: str) -> List[Dict[str, Any]]:
    """
    Get chat history for a user from Firestore.
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        List of chat messages
    """
    try:
        return firestore_service.get_chat_history(user_id)
    except Exception as e:
        logger.exception(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")

@router.post("/analytics")
async def log_analytics(event: AnalyticsEvent) -> Dict[str, str]:
    """
    Log an analytics event to Firestore.
    
    Args:
        event: The analytics event to log
        
    Returns:
        Status message
    """
    try:
        firestore_service.log_usage(event.event)
        return {"status": "logged"}
    except Exception as e:
        logger.exception(f"Error logging analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log analytics: {str(e)}") 