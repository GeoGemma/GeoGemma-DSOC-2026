from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import datetime

class LayerInfo(BaseModel):
    """Layer information for map visualization"""
    id: str
    tile_url: Optional[str] = None  # URL can be None if processing fails but metadata exists
    location: str
    processing_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opacity: float = 0.8
    visibility: str = "visible"
    metadata: Optional[Dict[str, Any]] = None

class AnalysisRequest(BaseModel):
    """Request for natural language analysis of satellite data"""
    prompt: str
    user_id: Optional[str] = None
    save_result: bool = False  # Default to False as DB is optional

class TimeSeriesRequest(BaseModel):
    """Request for time series analysis"""
    location: str
    processing_type: str
    start_date: str
    end_date: str
    interval: str = "monthly"
    user_id: Optional[str] = None

class CustomAreaRequest(BaseModel):
    """Request for custom area definition"""
    name: str
    description: Optional[str] = None
    geometry: Dict[str, Any]  # GeoJSON geometry
    user_id: Optional[str] = None

class ComparisonRequest(BaseModel):
    """Request for comparing two dates"""
    location: str
    processing_type: str
    date1: str
    date2: str
    user_id: Optional[str] = None

class AnalysisResult(BaseModel):
    """Result of prompt analysis"""
    location: str
    processing_type: str
    satellite: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    year: Optional[Union[int, str]] = None  # Allow 'latest' string too
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @validator('latitude')
    def validate_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

class ApiResponse(BaseModel):
    """Standard API response format"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class UserProfile(BaseModel):
    """User profile data"""
    user_id: str
    profile: Dict[str, Any]

class LayerData(BaseModel):
    """Layer data for saving"""
    user_id: str
    layer_id: str
    layer: Dict[str, Any]

class AnalysisData(BaseModel):
    """Analysis data for saving"""
    user_id: str
    analysis_id: str
    analysis: Dict[str, Any]

class ChatMessage(BaseModel):
    """Chat message for saving"""
    user_id: str
    message_id: str
    message: Dict[str, Any]

class CustomAreaData(BaseModel):
    """Custom area data for saving"""
    user_id: str
    area_id: str
    area: Dict[str, Any]

class AnalyticsEvent(BaseModel):
    """Analytics event data"""
    event: Dict[str, Any] 