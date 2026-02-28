import ee
import logging
import re
import random

logger = logging.getLogger(__name__)

def create_feature_collection_image(features, gee_collection, vis_params):
    """
    Convert a feature collection to an image for visualization.
    
    This is a generalized approach that works for all feature collections,
    applying appropriate styling based on geometry type.
    
    Args:
        features: ee.FeatureCollection object
        gee_collection: The GEE collection ID
        vis_params: Visualization parameters
        
    Returns:
        tuple: (ee.Image, visualization_params)
    """
    try:
        # For Open Buildings specifically, we'll use a different approach
        if 'open-buildings' in gee_collection:
            logger.info("Using specialized rendering for Open Buildings")
            
            # Create an empty image to paint on
            empty = ee.Image().byte()
            
            # Paint building outlines and fill with different colors
            # First paint the fill
            image = empty.paint(features, 1)  # Paint all pixels inside polygons with value 1
            
            # Use a simple single-band visualization for buildings
            visualization = {
                'palette': ['#FF0000'],  # Red for buildings
                'min': 0,
                'max': 1
            }
            return image, visualization
            
        # For all other feature collections, use a generalized approach
        logger.info(f"Using generalized feature collection visualization for: {gee_collection}")
        
        # Create an empty image to paint on
        empty = ee.Image().byte()
        
        # Get style parameters from vis_params or use defaults
        # Check if we're requesting a specific style type
        style_type = vis_params.get('style_type', 'default')
        
        # Define style based on style_type
        if style_type == 'outline_only':
            # For outline-only style (no fill)
            border_color = vis_params.get('color', '#4285F4')  # Google blue as default
            border_width = vis_params.get('width', 1.5)
            
            # Just paint the borders
            image = empty.paint(features, border_color, border_width)
            
            # Pass through visualization params
            visualization = vis_params
            
        elif style_type == 'random_colors':
            # For choropleth-like visualization with random colors
            # We'll use a numeric property to create a categorical visualization
            
            # First paint with random values based on feature index
            image = empty.paint(features, 'random')
            
            # Create a colorful palette
            colors = [
                '#4285F4', '#EA4335', '#FBBC05', '#34A853',  # Google colors
                '#0F9D58', '#DB4437', '#F4B400', '#0F9D58',
                '#46BDC6', '#DB4437', '#7BAAF7', '#F07B72',
                '#FDD663', '#71C287', '#B7E0CA', '#FAD2CF'
            ]
            
            visualization = {
                'min': 0,
                'max': len(colors) - 1,
                'palette': colors
            }
            
        else:
            # Default style with fill and border
            fill_color = vis_params.get('fillColor', '#4285F455')  # Semi-transparent blue
            border_color = vis_params.get('color', '#4285F4')      # Google blue
            border_width = vis_params.get('width', 1.0)            # Line width
            
            # First paint the fill
            filled = empty.paint(features, fill_color)
            
            # Then paint the borders
            image = filled.paint(features, border_color, border_width)
            
            # Pass through visualization params
            visualization = vis_params
        
        logger.info(f"Successfully created visualization for feature collection using style: {style_type}")
        return image, visualization
            
    except Exception as e:
        logger.error(f"Error painting features: {str(e)}")
        raise

def handle_sentinel1_visualization(gee_collection, date_range=None, point=None):
    """
    Special handling for Sentinel-1 SAR GRD data with polarization filtering.
    
    This function filters for VV polarization in IW (Interferometric Wide) mode
    and applies appropriate visualization for SAR data.
    
    Args:
        gee_collection: The GEE collection ID
        date_range: Optional date range override [start_date, end_date]
        point: Optional ee.Geometry.Point for location-based filtering
        
    Returns:
        tuple: (ee.Image, visualization_params)
    """
    logger.info("Detected Sentinel-1 dataset, applying special handling for polarization filtering")
    
    try:
        # Initialize the collection
        collection = ee.ImageCollection(gee_collection)
        
        # Apply date filtering if provided, otherwise use default April 2015
        if date_range and len(date_range) == 2:
            logger.info(f"Using provided date range: {date_range[0]} to {date_range[1]}")
            filtered_collection = collection.filterDate(date_range[0], date_range[1])
        else:
            # Default to April 2015 as specified
            logger.info("Using default date range: April 2015")
            filtered_collection = collection.filterDate('2015-04-01', '2015-04-30')
        
        # Apply point filtering if provided
        if point:
            logger.info("Applying spatial filter based on provided point")
            filtered_collection = filtered_collection.filterBounds(point)
        
        # Check available polarizations in the collection
        logger.info("Checking available polarizations in the collection")
        
        # Try to filter for VV polarization first (most common for land monitoring)
        vv_collection = filtered_collection.filter(
            ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')
        ).filter(
            ee.Filter.eq('instrumentMode', 'IW')  # Interferometric Wide mode
        )
        
        # If VV collection has images, use it
        vv_count = vv_collection.size().getInfo()
        logger.info(f"Found {vv_count} images with VV polarization")
        
        if vv_count > 0:
            logger.info("Using VV polarization for visualization")
            image = vv_collection.select('VV').mosaic()
            
            # Visualization parameters optimized for Sentinel-1 VV data
            vis_params = {
                'min': -25,
                'max': 0,
                'palette': ['000000', '0000FF', '00FFFF', 'FFFF00', 'FF0000', 'FFFFFF']
            }
            
        else:
            # Fallback to VH polarization
            logger.info("No VV polarization found, trying VH polarization")
            vh_collection = filtered_collection.filter(
                ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')
            ).filter(
                ee.Filter.eq('instrumentMode', 'IW')
            )
            
            vh_count = vh_collection.size().getInfo()
            logger.info(f"Found {vh_count} images with VH polarization")
            
            if vh_count > 0:
                logger.info("Using VH polarization for visualization")
                image = vh_collection.select('VH').mosaic()
                
                # Visualization parameters for VH (typically lower backscatter)
                vis_params = {
                    'min': -30,
                    'max': -5,
                    'palette': ['000000', '0000FF', '00FFFF', 'FFFF00', 'FF0000', 'FFFFFF']
                }
                
            else:
                # Final fallback: check for HH/HV polarization (used in some regions)
                logger.info("No VV/VH polarization found, trying HH polarization")
                hh_collection = filtered_collection.filter(
                    ee.Filter.listContains('transmitterReceiverPolarisation', 'HH')
                )
                
                if hh_collection.size().getInfo() > 0:
                    logger.info("Using HH polarization for visualization")
                    image = hh_collection.select('HH').mosaic()
                    
                    # Visualization parameters for HH
                    vis_params = {
                        'min': -25,
                        'max': 0,
                        'palette': ['000000', '0000FF', '00FFFF', 'FFFF00', 'FF0000', 'FFFFFF']
                    }
                    
                else:
                    # If all else fails, use whatever band is available
                    logger.info("Using first available image with any polarization")
                    first_img = filtered_collection.first()
                    bands = first_img.bandNames().getInfo()
                    logger.info(f"Available bands: {bands}")
                    
                    # Select the first SAR band (avoid angle and other metadata bands)
                    sar_bands = [b for b in bands if b in ['HH', 'HV', 'VV', 'VH']]
                    if sar_bands:
                        first_band = sar_bands[0]
                        logger.info(f"Selecting band: {first_band}")
                        image = first_img.select(first_band)
                        
                        vis_params = {
                            'min': -25,
                            'max': 0,
                            'palette': ['000000', '0000FF', '00FFFF', 'FFFF00', 'FF0000', 'FFFFFF']
                        }
                    else:
                        # Last resort
                        image = first_img
                        vis_params = {
                            'min': -25,
                            'max': 0,
                            'palette': ['000000', '0000FF', '00FFFF', 'FFFF00', 'FF0000', 'FFFFFF']
                        }
        
        return image, vis_params
        
    except Exception as e:
        logger.error(f"Error in Sentinel-1 visualization: {str(e)}")
        raise

def handle_open_buildings_temporal_visualization(gee_collection, point=None):
    """
    Special handling for the GOOGLE/Research/open-buildings-temporal/v1 dataset
    to display only the building_presence band in black and white.
    
    This function filters for the most recent timestamp at the given location
    and visualizes only the building_presence band.
    
    Args:
        gee_collection: The GEE collection ID
        point: Optional ee.Geometry.Point to filter by location. If None, a default point is used.
        
    Returns:
        tuple: (ee.Image, visualization_params)
    """
    logger.info("Detected Open Buildings Temporal dataset, applying special visualization for building_presence band")
    
    try:
        # Initialize Earth Engine collection
        collection = ee.ImageCollection(gee_collection)
        
        # Use a default point (New Cairo, Egypt) if none provided
        if point is None:
            point = ee.Geometry.Point([31.549876545106667, 30.011531513347673])
        
        # Filter collection by location
        filtered_collection = collection#.filterBounds(point)
        
        # Get the distinct timestamps sorted (most recent last)
        timestamps = filtered_collection.aggregate_array('system:time_start').distinct().sort()
        
        # Get the most recent timestamp
        latest_timestamp = ee.Number(timestamps.get(-1))
        
        logger.info(f"Filtering Open Buildings Temporal for the most recent timestamp")
        
        # Filter to the most recent timestamp and create a mosaic
        latest_image = filtered_collection.filter(
            ee.Filter.eq('system:time_start', latest_timestamp)
        ).mosaic()
        
        # Select only the building_presence band
        building_presence = latest_image.select('building_presence')
        
        # Create visualization parameters for black and white display
        # Values range from 0 to 1, where 0 = no building, 1 = building present
        vis_params = {
            'min': 0,
            'max': 1,
            'palette': ['#000000', '#FFFFFF']  # Black to white
        }
        
        logger.info("Using building_presence band with black and white visualization")
        
        # Return the image with only the building_presence band and the vis params
        return building_presence, vis_params
        
    except Exception as e:
        logger.error(f"Error in Open Buildings Temporal visualization: {str(e)}")
        raise

def filter_open_buildings(features, point=None, skip_confidence_filter=False, limit=5000):
    """Apply special filtering for Open Buildings dataset"""
    try:
        # Use Lagos, Nigeria coordinates as default if no point provided
        if point is None:
            point = ee.Geometry.Point([3.389, 6.492])
        
        # Create a buffer around the point of interest
        buffer_distance = 500  # 500 meters buffer
        buffer_region = point.buffer(buffer_distance)
        
        # Filter buildings to this region
        filtered = features.filterBounds(buffer_region)
        
        # Apply confidence filter unless specifically told to skip it
        if not skip_confidence_filter:
            logger.info("Applying confidence filter >= 0.65")
            filtered = filtered.filter('confidence >= 0.65')
        
        # Limit features to avoid timeouts
        filtered = filtered.limit(limit)
        logger.info(f"Successfully filtered Open Buildings with {limit} max features")
        
        return filtered
    except Exception as e:
        logger.error(f"Error during Open Buildings filtering: {str(e)}")
        
        # If filtering fails, try an even more limited approach
        try:
            logger.info("Filtering failed, trying a more limited approach")
            # Create a smaller buffer
            smaller_buffer = point.buffer(2000)  # 200 meters buffer
            return ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons').filterBounds(smaller_buffer).limit(500)
        except Exception as e2:
            logger.error(f"Second attempt also failed: {str(e2)}")
            raise RuntimeError(f"Error filtering Open Buildings: {str(e)}. Second attempt: {str(e2)}")

def handle_worldcover_visualization(gee_collection):
    """
    Special handling for ESA WorldCover datasets with proper categorical visualization
    
    This function uses explicit remapping to consecutive integers 
    to ensure proper categorical display of land cover classes.
    """
    logger.info("Detected ESA WorldCover dataset, applying special categorical visualization")
    
    try:
        # Get the first image from the collection
        worldcover = ee.ImageCollection(gee_collection).first()
        
        if 'v100' in gee_collection:
            # ESA WorldCover v100 class values
            original_values = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
            # Map to consecutive integers for better visualization
            remapped_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            
            # Create palette with proper format
            palette = [
                '#000000',  # No data (black)
                '#006400',  # Tree cover (dark green)
                '#ffbb22',  # Shrubland (orange)
                '#ffff4c',  # Grassland (yellow)
                '#f096ff',  # Cropland (pink)
                '#fa0000',  # Built-up (red)
                '#b4b4b4',  # Bare / sparse vegetation (grey)
                '#f0f0f0',  # Snow and ice (white)
                '#0064c8',  # Permanent water bodies (blue)
                '#0096a0'   # Herbaceous wetland (teal)
            ]
            
            # STEP 1: Explicitly remap the values to consecutive integers
            # This is CRITICAL for proper categorical rendering
            remapped_image = worldcover.select('Map').remap(
                original_values,
                remapped_values
            )
            
            # STEP 2: Create visualization parameters for the remapped image
            # Since we now have consecutive integers, min/max will work correctly
            vis_params = {
                'min': 0,
                'max': 9,
                'palette': palette
            }
            
            logger.info(f"Using WorldCover v100 remapped visualization with consecutive values 0-9")
            logger.info(f"Original values: {original_values}")
            logger.info(f"Remapped values: {remapped_values}")
            logger.info(f"Palette: {palette}")
            
            # Return the remapped image and the vis params
            return remapped_image, vis_params
            
        else:  # v200
            # ESA WorldCover v200 has additional classes
            original_values = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
            remapped_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
            
            # Create palette with proper format
            palette = [
                '#000000',  # No data (black)
                '#006400',  # Tree cover (dark green)
                '#ffbb22',  # Shrubland (orange)
                '#ffff4c',  # Grassland (yellow)
                '#f096ff',  # Cropland (pink)
                '#fa0000',  # Built-up (red)
                '#b4b4b4',  # Bare / sparse vegetation (grey)
                '#f0f0f0',  # Snow and ice (white)
                '#0064c8',  # Permanent water bodies (blue)
                '#0096a0',  # Herbaceous wetland (teal)
                '#00cf75',  # Mangroves (light green)
                '#fae6a0'   # Moss and lichen (light beige)
            ]
            
            # STEP 1: Explicitly remap the values to consecutive integers
            remapped_image = worldcover.select('Map').remap(
                original_values,
                remapped_values
            )
            
            # STEP 2: Create visualization parameters for the remapped image
            vis_params = {
                'min': 0,
                'max': 11,
                'palette': palette
            }
            
            logger.info(f"Using WorldCover v200 remapped visualization with consecutive values 0-11")
            logger.info(f"Original values: {original_values}")
            logger.info(f"Remapped values: {remapped_values}")
            logger.info(f"Palette: {palette}")
            
            # Return the remapped image and the vis params
            return remapped_image, vis_params
            
    except Exception as e:
        logger.error(f"Error in WorldCover visualization: {str(e)}")
        raise