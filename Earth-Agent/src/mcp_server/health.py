"""
Health check endpoints for the GIS AI Agent.

This module provides endpoints for checking the health and status of the application
and its dependencies.
"""

import os
import time
import logging
import platform
import socket
from typing import Dict, Any, List, Optional
import json
import asyncio

import pkg_resources

from ..config import get_config
from ..gemini.client import get_gemini_client

# Configure logging
logger = logging.getLogger(__name__)

# Define startup time
_startup_time = time.time()


async def get_health_status() -> Dict[str, Any]:
    """
    Get the health status of the application and its dependencies.
    
    Returns:
        Dictionary with health status information.
    """
    # Basic health information
    health_data = {
        "status": "healthy",
        "version": "0.2.0",
        "uptime_seconds": int(time.time() - _startup_time),
        "hostname": socket.gethostname(),
        "environment": os.environ.get("ENV", "production"),
        "timestamp": int(time.time()),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {},
        "services": {}
    }
    
    # Check config
    try:
        config = get_config()
        health_data["services"]["config"] = {"status": "up"}
    except Exception as e:
        logger.error(f"Config service check failed: {e}")
        health_data["services"]["config"] = {
            "status": "down",
            "error": str(e)
        }
        health_data["status"] = "degraded"
    
    # Check Gemini API
    try:
        gemini_status = await check_gemini_api()
        health_data["services"]["gemini_api"] = gemini_status
        if gemini_status["status"] != "up":
            health_data["status"] = "degraded"
    except Exception as e:
        logger.error(f"Gemini API check failed: {e}")
        health_data["services"]["gemini_api"] = {
            "status": "down",
            "error": str(e)
        }
        health_data["status"] = "degraded"
    
    # Check critical dependencies
    try:
        critical_deps = ["fastapi", "pydantic", "google-generativeai", 
                         "earthengine-api", "geopandas", "shapely"]
        
        # Collect version info
        for dep in critical_deps:
            try:
                version = pkg_resources.get_distribution(dep).version
                health_data["dependencies"][dep] = {"version": version, "status": "installed"}
            except pkg_resources.DistributionNotFound:
                health_data["dependencies"][dep] = {"status": "missing"}
                health_data["status"] = "degraded"
    except Exception as e:
        logger.error(f"Dependency check failed: {e}")
        health_data["dependencies"]["check_error"] = str(e)
    
    return health_data


async def check_gemini_api() -> Dict[str, Any]:
    """
    Check the connection to the Gemini API.
    
    Returns:
        Dictionary with Gemini API status information.
    """
    try:
        # Get Gemini client
        client = get_gemini_client()
        
        # Simple prompt to test API connectivity
        start_time = time.time()
        response = await client.generate_text("Return 'ok' if you can read this.")
        end_time = time.time()
        
        # Process response
        if response and "text" in response and "ok" in response["text"].lower():
            return {
                "status": "up",
                "latency_ms": int((end_time - start_time) * 1000),
                "model": client.model_name
            }
        else:
            return {
                "status": "degraded",
                "error": "Unexpected response format",
                "latency_ms": int((end_time - start_time) * 1000),
                "model": client.model_name
            }
    except Exception as e:
        logger.error(f"Gemini API check failed: {e}")
        return {
            "status": "down",
            "error": str(e)
        }


async def check_diagnostics() -> Dict[str, Any]:
    """
    Get detailed diagnostics information about the application.
    Only available in non-production environments.
    
    Returns:
        Dictionary with detailed diagnostics information.
    """
    # Basic health check
    health_data = await get_health_status()
    
    # Only provide detailed diagnostics in non-production environments
    if os.environ.get("ENV", "production") == "production":
        return {
            "status": health_data["status"],
            "message": "Detailed diagnostics are not available in production environment"
        }
    
    # Add memory usage
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        health_data["system"] = {
            "memory_usage_mb": round(memory_info.rss / (1024 * 1024), 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "thread_count": process.num_threads(),
            "open_files": len(process.open_files())
        }
    except (ImportError, Exception) as e:
        health_data["system"] = {"error": f"Could not collect system info: {e}"}
    
    # Additional environment information
    health_data["environment_details"] = {
        key: value for key, value in os.environ.items() 
        if not any(secret in key.lower() for secret in ["key", "token", "secret", "password", "cred"])
    }
    
    return health_data


def register_health_routes(app):
    """
    Register health check routes with the FastAPI application.
    
    Args:
        app: FastAPI application instance.
    """
    @app.get("/health")
    async def health():
        """Basic health check endpoint."""
        return await get_health_status()
    
    @app.get("/health/live")
    async def liveness():
        """Kubernetes liveness probe endpoint."""
        return {"status": "alive", "timestamp": int(time.time())}
    
    @app.get("/health/ready")
    async def readiness():
        """Kubernetes readiness probe endpoint."""
        health_data = await get_health_status()
        if health_data["status"] == "healthy":
            return {"status": "ready", "timestamp": int(time.time())}
        else:
            return {"status": "not_ready", "reason": health_data["status"], "timestamp": int(time.time())}
    
    @app.get("/diagnostics")
    async def diagnostics():
        """Detailed diagnostics endpoint (non-production only)."""
        return await check_diagnostics() 