# src/api/routers/pixel_value_router.py
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import ee
import logging
from datetime import datetime

from src.services.earth_engine_service import initialize_earth_engine, run_ee_operation, EE_INITIALIZED
from src.config.settings import Settings

# Set up router
router = APIRouter()

# Pydantic model for the request body
class PixelValueRequest(BaseModel):
    layer_id: str
    coordinates: List[float]  # [longitude, latitude]
    processing_type: str
    ee_collection_id: Optional[str] = None
    image_date: Optional[str] = None

class HistogramRequest(BaseModel):
    geometry: Dict[str, Any]  # GeoJSON geometry
    processing_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    ee_collection_id: Optional[str] = None
    band_name: Optional[str] = None
    scale: Optional[int] = None

# Get settings
settings = Settings()

@router.post("/pixel-value") 
async def get_pixel_value(request: PixelValueRequest = Body(...)):
    """Get the pixel value at specific coordinates for a layer."""
    try:
        # Ensure Earth Engine is initialized
        if not EE_INITIALIZED:
            success, error = await initialize_earth_engine(settings.ee_project_id)
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Earth Engine: {error}")
        
        # Extract coordinates
        if len(request.coordinates) != 2:
            raise HTTPException(status_code=400, detail="Coordinates must be [longitude, latitude]")
        
        lon, lat = request.coordinates
        point = ee.Geometry.Point(lon, lat)
        
        # Handle different processing types
        processing_type = request.processing_type.upper()
        
        async def get_image_and_sample():
            """Get the appropriate image and sample the pixel value"""
            image = None
            band_name = None
            scale = 30  # Default scale
            
            if request.ee_collection_id:
                # Use the provided collection ID
                try:
                    collection = ee.ImageCollection(request.ee_collection_id)
                    
                    # Filter by date if provided
                    if request.image_date:
                        date = datetime.strptime(request.image_date, '%Y-%m-%d')
                        collection = collection.filterDate(
                            ee.Date(date.strftime('%Y-%m-%d')),
                            ee.Date(date.strftime('%Y-%m-%d')).advance(1, 'day')
                        )
                    
                    # Get the first image (or median composite if multiple)
                    collection_size = await run_ee_operation(lambda: collection.size().getInfo())
                    if collection_size > 1:
                        image = collection.median()
                    else:
                        image = collection.first()
                    
                except ee.EEException as e:
                    logging.error(f"Error accessing collection {request.ee_collection_id}: {e}")
                    raise HTTPException(status_code=500, detail=f"Error accessing Earth Engine collection: {str(e)}")
            else:
                # Use default collections based on processing type
                if processing_type == 'NDVI':
                    collection = ee.ImageCollection('MODIS/006/MOD13Q1')
                    if request.image_date:
                        date = datetime.strptime(request.image_date, '%Y-%m-%d')
                        collection = collection.filterDate(
                            ee.Date(date.strftime('%Y-%m')),
                            ee.Date(date.strftime('%Y-%m')).advance(1, 'month')
                        )
                    image = collection.select('NDVI').median()
                    band_name = 'NDVI'
                    scale = 250  # MODIS NDVI native resolution
                elif processing_type == 'LST':
                    collection = ee.ImageCollection('MODIS/006/MOD11A1')
                    if request.image_date:
                        date = datetime.strptime(request.image_date, '%Y-%m-%d')
                        collection = collection.filterDate(
                            ee.Date(date.strftime('%Y-%m-%d')),
                            ee.Date(date.strftime('%Y-%m-%d')).advance(1, 'day')
                        )
                    image = collection.select('LST_Day_1km').median()
                    image = image.multiply(0.02).subtract(273.15).rename('LST_Celsius')
                    band_name = 'LST_Celsius'
                    scale = 1000  # MODIS LST native resolution
                elif processing_type == 'SURFACE WATER':
                    image = ee.Image('JRC/GSW1_3/GlobalSurfaceWater')
                    band_name = 'occurrence'
                    scale = 30
                elif processing_type == 'LULC':
                    image = ee.Image('ESA/WorldCover/v100/2020')
                    band_name = 'Map'
                    scale = 10
                elif processing_type == 'RGB':
                    collection = ee.ImageCollection('LANDSAT/LC08/C01/T1_TOA')
                    if request.image_date:
                        date = datetime.strptime(request.image_date, '%Y-%m-%d')
                        collection = collection.filterDate(
                            ee.Date(date.strftime('%Y-%m-%d')),
                            ee.Date(date.strftime('%Y-%m-%d')).advance(1, 'day')
                        ).sort('CLOUD_COVER')
                    image = collection.first()
                    rgb_bands = ['B4', 'B3', 'B2']
                    scale = 30
                elif processing_type == 'OPEN BUILDINGS':
                    # Use the Open Buildings dataset and select the building_height band
                    collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1')
                    filtered_col = collection.filterBounds(point)
                    latest_image = filtered_col.sort('system:time_start', False).first()
                    if latest_image is None:
                        raise HTTPException(status_code=404, detail="No Open Buildings data found at this location.")
                    latest_timestamp = latest_image.get('system:time_start')
                    mosaic = filtered_col.filter(ee.Filter.eq('system:time_start', latest_timestamp)).mosaic()
                    image = mosaic.select('building_height')
                    band_name = 'building_height'
                    scale = 4  # Open Buildings native resolution is 4m
                elif processing_type in ['CO', 'NO2', 'CH4', 'SO2']:
                    # Gas concentrations
                    if processing_type == 'CO':
                        collection = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_CO')
                        band_name = 'CO_column_number_density'
                    elif processing_type == 'NO2':
                        collection = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2')
                        band_name = 'NO2_column_number_density'
                    elif processing_type == 'CH4':
                        collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_CH4')
                        band_name = 'CH4_column_volume_mixing_ratio_dry_air'
                    elif processing_type == 'SO2':
                        collection = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_SO2')
                        band_name = 'SO2_column_number_density'
                    
                    # Filter by date if provided
                    if request.image_date:
                        date = datetime.strptime(request.image_date, '%Y-%m-%d')
                        collection = collection.filterDate(
                            ee.Date(date.strftime('%Y-%m-%d')),
                            ee.Date(date.strftime('%Y-%m-%d')).advance(1, 'day')
                        )
                    
                    image = collection.select(band_name).median()
                    scale = 7000  # Sentinel-5P native resolution
                elif processing_type == 'ACTIVE_FIRE' or processing_type == 'ACTIVE FIRE':
                    collection = ee.ImageCollection('FIRMS')
                    if request.image_date:
                        date = datetime.strptime(request.image_date, '%Y-%m-%d')
                        collection = collection.filterDate(
                            ee.Date(date.strftime('%Y-%m-%d')),
                            ee.Date(date.strftime('%Y-%m-%d')).advance(1, 'day')
                        )
                    image = collection.select('T21').median()
                    band_name = 'T21'
                    scale = 375
                else:
                    raise HTTPException(status_code=400, 
                                      detail=f"Unsupported processing type: {processing_type}")
            
            if image is None:
                raise HTTPException(status_code=404, 
                                  detail="No image found for the given parameters")
            
            # Sample the pixel value at the point
            if processing_type == 'RGB':
                def sample_rgb():
                    rgb_bands = ['B4', 'B3', 'B2']
                    sample = image.select(rgb_bands).sample(point, scale).first()
                    if sample is None:
                        return None
                    sample_info = sample.getInfo()
                    if sample_info is None or 'properties' not in sample_info:
                        return None
                    value_info = sample_info['properties']
                    r_val = int(value_info.get('B4', 0) * 255)
                    g_val = int(value_info.get('B3', 0) * 255)
                    b_val = int(value_info.get('B2', 0) * 255)
                    return {
                        'r': r_val,
                        'g': g_val,
                        'b': b_val
                    }
                value = await run_ee_operation(sample_rgb)
                if value is None:
                    raise HTTPException(status_code=404, detail="No RGB pixel data found at this location.")
            else:
                def sample_band():
                    sample = image.sample(point, scale).first()
                    if sample is None:
                        return None
                    sample_info = sample.getInfo()
                    if sample_info is None or 'properties' not in sample_info:
                        return None
                    value_info = sample_info['properties']
                    return value_info.get(band_name, None)
                value = await run_ee_operation(sample_band)
                if value is None:
                    raise HTTPException(status_code=404, detail=f"No {processing_type} pixel data found at this location.")
                # Special handling for LULC (categorical)
                if processing_type == 'LULC':
                    value = int(value)
                # Special handling for NDVI (scale to -1 to 1)
                if processing_type == 'NDVI' and value is not None:
                    value = float(value) / 10000.0  # MODIS NDVI scaling
            
            return value
        
        # Get the pixel value using the async helper function
        value = await get_image_and_sample()

        # Return the result
        return {
            "success": True,
            "value": value,
            "processing_type": processing_type,
            "coordinates": request.coordinates
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logging.exception(f"Error in pixel value endpoint: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch pixel value: {str(e)}"
        }

@router.post("/histogram")
async def get_histogram(request: HistogramRequest = Body(...)):
    """Get a histogram of values for a given geometry and processing type."""
    try:
        if not EE_INITIALIZED:
            success, error = await initialize_earth_engine(settings.ee_project_id)
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Earth Engine: {error}")

        # Parse geometry
        try:
            geom = ee.Geometry(request.geometry)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid geometry: {e}")

        processing_type = request.processing_type.upper()
        band_name = request.band_name
        scale = request.scale or 250  # Default for NDVI
        image = None

        # Select image and band
        if request.ee_collection_id:
            collection = ee.ImageCollection(request.ee_collection_id)
            if request.start_date and request.end_date:
                collection = collection.filterDate(request.start_date, request.end_date)
            image = collection.median()
            if not band_name:
                band_name = image.bandNames().getInfo()[0]
        else:
            if processing_type == 'NDVI':
                collection = ee.ImageCollection('MODIS/006/MOD13Q1')
                if request.start_date and request.end_date:
                    collection = collection.filterDate(request.start_date, request.end_date)
                image = collection.select('NDVI').median()
                band_name = 'NDVI'
                scale = 250
            elif processing_type == 'LST':
                collection = ee.ImageCollection('MODIS/006/MOD11A1')
                if request.start_date and request.end_date:
                    collection = collection.filterDate(request.start_date, request.end_date)
                image = collection.select('LST_Day_1km').median()
                image = image.multiply(0.02).subtract(273.15).rename('LST_Celsius')
                band_name = 'LST_Celsius'
                scale = 1000
            elif processing_type == 'LULC':
                image = ee.Image('ESA/WorldCover/v100/2020')
                band_name = 'Map'
                scale = 10
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported processing type: {processing_type}")

        if image is None or band_name is None:
            raise HTTPException(status_code=404, detail="No image or band found for the given parameters")

        # Compute histogram
        def compute_hist():
            reducer = ee.Reducer.histogram(maxBuckets=50)
            result = image.select(band_name).reduceRegion(
                reducer=reducer,
                geometry=geom,
                scale=scale,
                maxPixels=1e9,
                bestEffort=True
            )
            return result.get(band_name).getInfo()

        hist = await run_ee_operation(compute_hist)
        if not hist:
            raise HTTPException(status_code=404, detail="No histogram data found for this area.")

        # For NDVI, scale bucketMeans
        if processing_type == 'NDVI' and 'bucketMeans' in hist:
            hist['bucketMeans'] = [x / 10000.0 for x in hist['bucketMeans']]

        return {
            "success": True,
            "histogram": hist
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Error in histogram endpoint: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch histogram: {str(e)}"
        }