"""
API routers for the application.
"""

from .analysis_router import router as analysis_router
from .time_series_router import router as time_series_router
from .layers_router import router as layers_router
from .user_router import router as user_router
from .chat_router import router as chat_router
from .custom_areas_router import router as custom_areas_router
from .health_router import router as health_router

__all__ = [
    'analysis_router',
    'time_series_router',
    'layers_router',
    'user_router',
    'chat_router',
    'custom_areas_router',
    'health_router'
] 