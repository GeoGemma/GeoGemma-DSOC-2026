import logging
import os
from fastapi import APIRouter, Depends
from typing import Dict, Any

from src.services.earth_engine_service import get_ee_status
from src.services.genai_service import get_genai_status

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint that reports on the status of services.
    
    Returns:
        JSON with status information
    """
    # Get service statuses
    ee_status = get_ee_status()
    genai_status = get_genai_status()
    
    status = "ok"
    diagnostics = {
        "ee_initialized": ee_status["initialized"],
        "ee_error": ee_status["error"],
        "ee_project_id_configured": os.environ.get("EE_PROJECT_ID", "Not Set"),
        "llm_initialized": genai_status["initialized"],
        "llm_error": genai_status["error"],
        "llm_model": genai_status["model"] or os.environ.get("GEMINI_MODEL", "gemma-3-4b-it"),
        "version": "1.1.0",
    }
    
    # Check if services are healthy
    if not ee_status["initialized"] or not genai_status["initialized"]:
        status = "degraded"
        logger.warning(f"Health check status: {status}. Diagnostics: {diagnostics}")
    else:
        logger.info(f"Health check status: {status}")

    return {"status": status, "diagnostics": diagnostics} 