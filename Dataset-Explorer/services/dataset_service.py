import logging
import ee
from services.earth_engine import (
    filter_open_buildings, 
    create_feature_collection_image, 
    handle_worldcover_visualization,
    handle_open_buildings_temporal_visualization,
    handle_sentinel1_visualization
)
from config import Config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_best_scale_for_dataset(dataset_id):
    """
    Determine the appropriate scale to use for pixel value sampling based on dataset type.
    
    Parameters:
    dataset_id (str): The dataset ID
    
    Returns:
    int: The recommended scale in meters
    """
    # Default scale (Landsat resolution)
    default_scale = 30
    
    # High-resolution datasets
    if any(x in dataset_id for x in ['Sentinel2', 'S2', 'NAIP', 'HLS']):
        return 10  # 10m resolution for Sentinel-2 bands
        
    # Medium resolution datasets
    elif any(x in dataset_id for x in ['Landsat', 'LANDSAT', 'Sentinel1', 'S1']):
        return 30  # 30m resolution for Landsat and S1
        
    # Low resolution datasets
    elif any(x in dataset_id for x in ['MODIS', 'VIIRS', 'GOES', 'TROPOMI']):
        return 250  # MODIS typical resolution
        
    # Global climate datasets
    elif any(x in dataset_id for x in ['ERA5', 'GLDAS', 'CHIRPS']):
        return 1000  # ~1km climate data
    
    # Land cover classification
    elif any(x in dataset_id for x in ['landcover', 'WorldCover', 'NLCD']):
        return 30  # Typical land cover resolution
    
    # DEM datasets
    elif any(x in dataset_id for x in ['DEM', 'SRTM', 'elevation']):
        return 30  # SRTM resolution
    
    # For unknown datasets, use default
    return default_scale


def apply_temporal_filter_to_collection(collection, temporal_filter=None, dataset=None):
    """
    Apply temporal filtering to an image collection with enhanced error handling.
    
    Parameters:
    collection (ee.ImageCollection): The collection to filter
    temporal_filter (dict): Optional temporal filter parameters (start_date, end_date, aggregation)
    dataset (dict): Optional dataset metadata for fallback temporal info
    
    Returns:
    tuple: (filtered_collection, date_range, aggregation_method)
    """
    logger = logging.getLogger(__name__)
    
    # Set default values
    date_range = None
    aggregation_method = None
    
    # Check for known datasets with date range issues
    dataset_id = dataset.get('id', '') if dataset else ''
    if dataset_id and any(x in dataset_id for x in ['DEM', 'SRTM', 'ELEVATION', 'FAO/SOFO', 'COPERNICUS/DEM']):
        # For DEMs and datasets with date issues, use a wide date range
        date_range = ['1950-01-01', '2025-12-31']
        logger.info(f"Using special wide date range for static dataset or dataset with date issues: {date_range}")
        try:
            # Although we use a wide date range, some collections don't support date filtering
            # Try without date filtering first if this is a known problematic dataset
            if any(x in dataset_id for x in ['FAO/SOFO']):
                logger.info("Using collection without date filtering for known problematic dataset")
                return collection, date_range, aggregation_method
            # Otherwise try with the wide date range
            return collection.filterDate(date_range[0], date_range[1]), date_range, aggregation_method
        except Exception as e:
            logger.warning(f"Date filtering not supported for this dataset: {str(e)}")
            return collection, date_range, aggregation_method
    
    try:
        # First priority: Use provided temporal filter
        if temporal_filter and 'start_date' in temporal_filter and 'end_date' in temporal_filter:
            start_date = temporal_filter['start_date']
            end_date = temporal_filter['end_date']
            date_range = [start_date, end_date]
            aggregation_method = temporal_filter.get('aggregation')
            
            logger.info(f"Using provided temporal filter: {start_date} to {end_date}")
            if aggregation_method:
                logger.info(f"Using aggregation method: {aggregation_method}")
                
            filtered_collection = collection.filterDate(start_date, end_date)
            
        # Second priority: Use date range from dataset
        elif dataset:
            date_range = get_date_range(dataset)
            logger.info(f"Using date range from dataset: {date_range}")
            
            filtered_collection = collection.filterDate(date_range[0], date_range[1])
            
        # Third priority: Use default recent time window
        else:
            now = datetime.now()
            three_months_ago = now - timedelta(days=90)
            
            start_date = three_months_ago.strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            date_range = [start_date, end_date]
            
            logger.info(f"Using default recent time window: {start_date} to {end_date}")
            filtered_collection = collection.filterDate(start_date, end_date)
            
        # Check if filtering produced valid results
        try:
            count = filtered_collection.size().getInfo()
            logger.info(f"Filtered collection contains {count} images")
            
            if count == 0:
                logger.warning("No images found in date range, using unfiltered collection")
                filtered_collection = collection
                
        except Exception as e:
            logger.warning(f"Error checking filtered collection size: {str(e)}")
            filtered_collection = collection
            
        return filtered_collection, date_range, aggregation_method
        
    except Exception as e:
        logger.error(f"Error applying temporal filter: {str(e)}")
        # Return original collection if filtering fails
        return collection, None, None
    

def get_image_from_collection(collection, date_range=None, aggregation_method=None, dataset_id=None):
    """
    Select an appropriate image from a collection based on temporal parameters
    and dataset characteristics.
    
    Parameters:
    collection (ee.ImageCollection): The collection to process
    date_range (list): Optional date range [start_date, end_date]
    aggregation_method (str): Optional aggregation method ('median', 'mean', etc.)
    dataset_id (str): Optional dataset ID for type-specific handling
    
    Returns:
    ee.Image: The selected or aggregated image
    """
    logger = logging.getLogger(__name__)
    
    try:
        # First priority: Apply the specified aggregation method
        if aggregation_method == 'median':
            logger.info(f"Computing median mosaic for collection")
            return collection.median()
            
        elif aggregation_method == 'mean':
            logger.info(f"Computing mean mosaic for collection")
            return collection.mean()
            
        elif aggregation_method == 'max':
            logger.info(f"Computing max mosaic for collection")
            return collection.max()
            
        elif aggregation_method == 'min':
            logger.info(f"Computing min mosaic for collection")
            return collection.min()
        
        # Second priority: Based on dataset characteristics
        
        # High-cadence time series (MODIS, VIIRS, etc.)
        if dataset_id and any(x in dataset_id for x in ['MODIS', 'VIIRS', 'GOES']):
            logger.info(f"Using most recent image for high-cadence dataset")
            return collection.sort('system:time_start', False).first()
            
        # For Landsat/Sentinel, create a median composite by default
        elif dataset_id and any(x in dataset_id for x in ['LANDSAT', 'Sentinel', 'COPERNICUS']):
            logger.info(f"Creating median mosaic for Landsat/Sentinel")
            return collection.median()
            
        # Global climate datasets 
        elif dataset_id and any(x in dataset_id for x in ['ERA5', 'GLDAS', 'ECMWF']):
            logger.info(f"Creating mean mosaic for climate dataset")
            return collection.mean()
        
        # Default approach for other datasets
        else:
            # Try with recent image first, fall back to mosaic
            try:
                logger.info(f"Trying most recent image as default approach")
                recent = collection.sort('system:time_start', False).first()
                
                # Check if the recent image has any bands
                band_count = len(recent.bandNames().getInfo())
                if band_count > 0:
                    return recent
                else:
                    logger.info(f"Recent image has no bands, creating mosaic instead")
                    return collection.mosaic()
            except:
                logger.info(f"Failed to get recent image, creating mosaic instead")
                return collection.mosaic()
                
    except Exception as e:
        logger.error(f"Error selecting image from collection: {str(e)}")
        # Last resort: Just get the first image
        return collection.first()

def handle_palette_colors(palette):
    """
    Process palette colors to ensure they are in the correct format.
    Handles both hex codes and named colors.
    
    Parameters:
    palette (list): List of color values which may be hex codes or named colors
    
    Returns:
    list: Properly formatted palette
    """
    if not palette:
        return None
        
    # Common CSS color names with their hex equivalents 
    color_name_map = {
        'black': '#000000',
        'silver': '#C0C0C0',
        'gray': '#808080',
        'grey': '#808080',
        'white': '#FFFFFF',
        'maroon': '#800000',
        'red': '#FF0000',
        'purple': '#800080',
        'fuchsia': '#FF00FF',
        'green': '#008000',
        'lime': '#00FF00',
        'olive': '#808000',
        'yellow': '#FFFF00',
        'navy': '#000080',
        'blue': '#0000FF',
        'teal': '#008080',
        'aqua': '#00FFFF',
        'cyan': '#00FFFF',
        'orange': '#FFA500'
    }
    
    processed_palette = []
    
    for color in palette:
        if not color:  # Skip empty values
            continue
            
        color = color.lower() if isinstance(color, str) else color
        
        if isinstance(color, str):
            # Check if it's a named color
            if color in color_name_map:
                processed_palette.append(color_name_map[color])
            # Check if it's a hex code without # prefix
            elif all(c in '0123456789abcdefABCDEF' for c in color) and len(color) in [3, 6]:
                processed_palette.append('#' + color)
            # Otherwise assume it's already properly formatted
            else:
                processed_palette.append(color)
        else:
            # Non-string value, just add it as is
            processed_palette.append(color)
    
    return processed_palette if processed_palette else None



def extract_visualization_params(dataset):
    """Extract visualization parameters from dataset metadata with support for named colors"""
    bands = None
    palette = None
    min_val = 0
    max_val = 255  # Default for better RGB visualization
    class_descriptions = None
    
    # Try to get visualization params from primary location in STAC
    try:
        if 'summaries' in dataset and 'gee:visualizations' in dataset['summaries'] and dataset['summaries']['gee:visualizations']:
            vis = dataset['summaries']['gee:visualizations'][0]
            if 'image_visualization' in vis and 'band_vis' in vis['image_visualization']:
                band_vis = vis['image_visualization']['band_vis']
                palette = band_vis.get('palette', None)
                bands = band_vis.get('bands', None)
                min_val = band_vis.get('min', 0)
                max_val = band_vis.get('max', 255)
                
                # Process palette if it exists
                if palette:
                    logger.info(f"Found raw palette: {palette}")
                    palette = handle_palette_colors(palette)
                    logger.info(f"Processed palette: {palette}")
    except Exception as e:
        logger.warning(f"Error getting primary visualization params: {str(e)}")
    
    # Try alternative location for palette in STAC if not found
    if not palette or not bands:
        try:
            if 'summaries' in dataset and 'eo:bands' in dataset['summaries'] and dataset['summaries']['eo:bands']:
                gee_classes = dataset['summaries']['eo:bands'][0].get('gee:classes', [])
                if gee_classes and isinstance(gee_classes, list):
                    raw_palette = [item.get('color', '') for item in gee_classes if 'color' in item]
                    logger.info(f"Found raw palette from classes: {raw_palette}")
                    palette = handle_palette_colors(raw_palette)
                    logger.info(f"Processed palette from classes: {palette}")
                    class_descriptions = gee_classes
                    
                    # For classes, typically we use the first band
                    if not bands and 'eo:bands' in dataset['summaries']:
                        bands = [dataset['summaries']['eo:bands'][0].get('name', None)]
                
                # If we still don't have bands but we have band information, try to extract them
                elif not bands and 'eo:bands' in dataset['summaries'] and len(dataset['summaries']['eo:bands']) > 0:
                    # Extract band names from eo:bands
                    bands = [band.get('name') for band in dataset['summaries']['eo:bands'] if 'name' in band]
                    
                    # If we have exactly 3 bands, we might be dealing with an RGB dataset
                    if len(bands) == 3:
                        logger.info(f"Found 3 potential RGB bands: {bands}")
        except Exception as e:
            logger.warning(f"Error getting alternative visualization params: {str(e)}")
    
    # Check for JavaScript-derived visualization info as a fallback
    if (not palette or not bands) and isinstance(dataset, dict) and 'js_visualization_info' in dataset:
        js_info = dataset['js_visualization_info']
        logger.info(f"Checking JavaScript visualization info as fallback")
        
        # Use JS-derived bands if needed
        if not bands and 'vis_bands' in js_info:
            bands = js_info['vis_bands']
            logger.info(f"Using bands from JS example: {bands}")
        
        # Use JS-derived palette if needed
        if not palette and 'vis_palette' in js_info:
            js_palette = js_info['vis_palette']
            # Process the JavaScript palette for named colors
            logger.info(f"Found raw palette from JS example: {js_palette}")
            palette = handle_palette_colors(js_palette)
            logger.info(f"Processed palette from JS example: {palette}")
        
        # Use JS-derived min/max if needed
        if 'vis_min' in js_info:
            min_val = js_info['vis_min']
        if 'vis_max' in js_info:
            max_val = js_info['vis_max']
            
        # Also check selected_bands as fallback
        if not bands and 'selected_bands' in js_info:
            bands = js_info['selected_bands']
            logger.info(f"Using selected bands from JS example: {bands}")
    
    # If we still don't have bands but dataset has 'bands' property, use it
    if not bands and 'bands' in dataset:
        bands = dataset['bands']
        
    # Build visualization parameters
    vis_params = {'min': min_val, 'max': max_val}
    if palette:
        vis_params['palette'] = palette
    if bands:
        vis_params['bands'] = bands
    
    logger.info(f"Final vis_params: {vis_params}")
    return vis_params, bands, palette, class_descriptions


def get_date_range(dataset):
    """Extract date range from dataset metadata with improved handling for all datasets
    
    Returns a suitable date range for visualization, prioritizing:
    1. JavaScript visualization info temporal filter
    2. Dataset temporal extent
    3. Fallback reasonable defaults based on dataset type
    """
    # Check for dataset ID to apply specific rules
    dataset_id = dataset.get('id', '')
    
    # Special handling for datasets known to have date range issues
    if any(x in dataset_id for x in ['DEM', 'SRTM', 'ELEVATION', 'AUSTRALIA_5M_DEM', 'FAO/SOFO', 'COPERNICUS/DEM']):
        # For DEMs and datasets with date issues, use a wide date range
        date_range = ['1950-01-01', '2025-12-31']
        logger.info(f"Using special wide date range for static dataset or dataset with date issues: {date_range}")
        return date_range
    
    # First priority: Check JS visualization info for temporal filter
    if isinstance(dataset, dict) and 'js_visualization_info' in dataset:
        js_info = dataset['js_visualization_info']
        if 'temporal_filter' in js_info:
            tf = js_info['temporal_filter']
            if 'start_date' in tf and 'end_date' in tf:
                js_date_range = [tf['start_date'], tf['end_date']]
                logger.info(f"Using temporal filter from JS info: {js_date_range}")
                return js_date_range
    
    # Second priority: Use dataset timeline from extent.temporal.interval
    temporal_interval = dataset.get('extent', {}).get('temporal', {}).get('interval', None)
    if (
        temporal_interval and 
        isinstance(temporal_interval, list) and 
        len(temporal_interval) > 0 and 
        isinstance(temporal_interval[0], list) and 
        len(temporal_interval[0]) == 2         
    ):
        date_range = temporal_interval[0]
        logger.info(f"Using temporal interval from dataset: {date_range}")
    else:
        # Third priority: Use dataset date_range property if available
        date_range = dataset.get('date_range')
        if date_range:
            logger.info(f"Using date_range property: {date_range}")
        else:
            # Fourth priority: Apply smart defaults based on dataset type
            
            # Special case for static datasets
            if any(x in dataset_id for x in ['DEM', 'SRTM', 'ELEVATION', 'BOUNDARIES']):
                # Static datasets don't need specific date ranges
                date_range = ['1950-01-01', '2025-12-31']
                logger.info(f"Using wide date range for static dataset: {date_range}")
            
            # For time series datasets, use recent data (last 3 months)
            elif any(x in dataset_id for x in ['MODIS', 'VIIRS', 'GOES', 'GLDAS', 'TROPOMI']):
                from datetime import datetime, timedelta
                today = datetime.now()
                three_months_ago = today - timedelta(days=90)
                date_range = [three_months_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')]
                logger.info(f"Using recent 3-month window for time series: {date_range}")
            
            # For Landsat/Sentinel, use a 1-year window for better mosaics
            elif any(x in dataset_id for x in ['LANDSAT', 'SENTINEL', 'COPERNICUS']):
                from datetime import datetime, timedelta
                today = datetime.now()
                one_year_ago = today - timedelta(days=365)
                date_range = [one_year_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')]
                logger.info(f"Using 1-year window for Landsat/Sentinel: {date_range}")
            
            # Default fallback
            else:
                date_range = ['1950-01-01', '2025-12-31']
                logger.info(f"Using default wide date range: {date_range}")
    
    # Check and fix chronological order if needed
    if date_range and len(date_range) == 2:
        # Convert dates to string format if they aren't already
        start_date = str(date_range[0])
        end_date = str(date_range[1])
        
        # Compare dates (works for ISO format strings like '2015-01-01T00:00:00Z')
        if start_date > end_date:
            logger.warning(f"Date range for {dataset_id} is in reverse order: {date_range}. Swapping to ensure chronological order.")
            return [end_date, start_date]  # Swap to ensure chronological order
    
    return date_range


def get_spatial_extent(dataset):
    """Extract bounding box from dataset metadata"""
    try:
        if 'extent' in dataset and 'spatial' in dataset['extent'] and 'bbox' in dataset['extent']['spatial']:
            return dataset['extent']['spatial']['bbox'][0]  # Get the first bbox if multiple exist
    except Exception as e:
        logger.warning(f"Error getting bbox: {str(e)}")
    return None

def get_lookat(dataset):
    """Extract lookat information from dataset metadata"""
    try:
        if 'summaries' in dataset and 'gee:visualizations' in dataset['summaries'] and dataset['summaries']['gee:visualizations']:
            return dataset['summaries']['gee:visualizations'][0].get('lookat', None)
    except Exception as e:
        logger.warning(f"Error getting lookat: {str(e)}")
    return None

def get_feature_properties(features, gee_collection):
    """Extract properties from a feature collection"""
    feature_properties = []
    
    try:
        # For open buildings, we know the properties
        if 'open-buildings' in gee_collection:
            feature_properties = ['confidence', 'area_in_meters', 'full_plus_code']
        else:
            # For other collections, try to extract from GEE
            sample_features = features.limit(1).getInfo()
            if sample_features and 'features' in sample_features and len(sample_features['features']) > 0:
                feature_properties = list(sample_features['features'][0]['properties'].keys())
    except Exception as e:
        logger.warning(f"Error getting feature properties: {str(e)}")
    
    return feature_properties

def validate_map_center(map_center):
    """
    Validates map center coordinates to ensure they're in the correct range.
    
    Parameters:
    map_center (dict): Map center info with lon, lat, zoom keys
    
    Returns:
    dict: Validated map center or None if invalid
    """
    if not map_center:
        return None
        
    # Extract values
    lon = map_center.get('lon')
    lat = map_center.get('lat')
    zoom = map_center.get('zoom')
    
    # Validate the coordinates
    valid = True
    
    # Check if latitude is in valid range (-90 to 90)
    if lat is not None and (lat < -90 or lat > 90):
        logger.warning(f"Invalid latitude value: {lat}. Should be between -90 and 90.")
        valid = False
    
    # Check if longitude is in valid range (-180 to 180)
    if lon is not None and (lon < -180 or lon > 180):
        logger.warning(f"Invalid longitude value: {lon}. Should be between -180 and 180.")
        valid = False
    
    # Check zoom level (typically between 0-22)
    if zoom is not None and (zoom < 0 or zoom > 22):
        logger.warning(f"Unusual zoom level: {zoom}. Using default zoom.")
        zoom = 8  # Set a reasonable default
    
    if not valid:
        logger.warning(f"Invalid map center: {map_center}")
        return None
    
    return {
        'lon': lon,
        'lat': lat,
        'zoom': zoom if zoom is not None else 8
    }


def process_dataset_for_visualization(dataset, limit_features=None, skip_confidence_filter=False):
    """Process a dataset for visualization on the map"""
    if limit_features is None:
        limit_features = Config.FEATURE_LIMIT
        
    # Get the dataset ID and GEE collection ID
    dataset_id = dataset['id']
    gee_collection = dataset.get('gee_id', dataset_id)
    logger.info(f"GEE collection identifier: {gee_collection}")
    
    # Call debug function to log visualization parameters
    debug_visualization_params(dataset)
    
    # Get date range
    date_range = get_date_range(dataset)
    logger.info(f"Using date range: {date_range}")
    
    # Determine the type: "image", "image_collection", or "table" (for FeatureCollection)
    gee_type = dataset.get('gee:type', 'image_collection')
    logger.info(f"Dataset type: {gee_type}")
    
    # Extract visualization parameters
    vis_params, bands, palette, class_descriptions = extract_visualization_params(dataset)
    
    # Default color for FeatureCollections if no palette is specified
    if gee_type.lower() == 'table' and not palette:
        vis_params['palette'] = ['#FF0000']  # Default to red for buildings/features
    
    logger.info(f"Visualization parameters: {vis_params}")
    
    # Process the dataset based on its type
    try:
        if gee_type.lower() == 'table':
            return process_feature_collection(
                gee_collection, 
                vis_params, 
                limit_features, 
                skip_confidence_filter
            )
        elif gee_type.lower() == 'image':
            return process_image(gee_collection, vis_params)
        else:
            # Pass the entire dataset to process_image_collection
            return process_image_collection(
                gee_collection, 
                date_range, 
                vis_params,
                dataset  # Added dataset parameter to use JS visualization info
            )
    except Exception as e:
        logger.error(f"Error processing dataset {dataset_id}: {str(e)}")
        raise

def debug_visualization_params(dataset):
    """
    Print detailed visualization parameters for debugging purposes.
    This function extracts and logs all available visualization information
    without modifying any existing functionality.
    
    Parameters:
    dataset (dict): The dataset metadata dictionary
    """
    dataset_id = dataset['id']
    gee_id = dataset.get('gee_id', dataset_id)
    
    logger.info(f"==== DEBUGGING VISUALIZATION PARAMS FOR {dataset_id} ====")
    logger.info(f"GEE ID: {gee_id}")
    
    # Extract basic dataset type
    gee_type = dataset.get('gee:type', 'image_collection')
    logger.info(f"Dataset type: {gee_type}")
    
    # Log date range
    date_range = get_date_range(dataset)
    logger.info(f"Date Range: {date_range}")
    
    # Log spatial extent
    bbox = get_spatial_extent(dataset)
    logger.info(f"Spatial Extent (BBOX): {bbox}")
    
    # Log lookat information
    lookat = get_lookat(dataset)
    logger.info(f"Look At parameters: {lookat}")
    
    # Extract visualization parameters in detail
    logger.info("=== PRIMARY VISUALIZATION PARAMETERS ===")
    if 'summaries' in dataset and 'gee:visualizations' in dataset['summaries']:
        vis_list = dataset['summaries']['gee:visualizations']
        logger.info(f"Found {len(vis_list)} visualization entries")
        
        for i, vis in enumerate(vis_list):
            logger.info(f"Visualization #{i+1}:")
            
            # Log visualization name if available
            if 'name' in vis:
                logger.info(f"  Name: {vis['name']}")
                
            # Log display name if available
            if 'display_name' in vis:
                logger.info(f"  Display Name: {vis['display_name']}")
                
            # Log image visualization parameters
            if 'image_visualization' in vis:
                img_vis = vis['image_visualization']
                logger.info(f"  Image Visualization: {img_vis}")
                
                if 'band_vis' in img_vis:
                    band_vis = img_vis['band_vis']
                    logger.info(f"  Bands: {band_vis.get('bands', 'Not specified')}")
                    logger.info(f"  Min: {band_vis.get('min', 'Not specified')}")
                    logger.info(f"  Max: {band_vis.get('max', 'Not specified')}")
                    logger.info(f"  Palette: {band_vis.get('palette', 'Not specified')}")
                    logger.info(f"  Gamma: {band_vis.get('gamma', 'Not specified')}")
    else:
        logger.info("No gee:visualizations found")
    
    # Extract band information
    logger.info("=== BAND INFORMATION ===")
    if 'summaries' in dataset and 'eo:bands' in dataset['summaries']:
        bands = dataset['summaries']['eo:bands']
        logger.info(f"Found {len(bands)} band entries")
        
        for i, band in enumerate(bands):
            logger.info(f"Band #{i+1}:")
            logger.info(f"  Name: {band.get('name', 'Unnamed')}")
            logger.info(f"  Description: {band.get('description', 'No description')}")
            logger.info(f"  Center Wavelength: {band.get('center_wavelength', 'Not specified')}")
            
            # Check for gee:classes (important for classified images)
            if 'gee:classes' in band:
                classes = band['gee:classes']
                logger.info(f"  Found {len(classes)} classes")
                for j, cls in enumerate(classes):
                    logger.info(f"    Class #{j+1}: Value={cls.get('value', 'No value')}, "
                               f"Description={cls.get('description', 'No description')}, "
                               f"Color={cls.get('color', 'No color')}")
    else:
        logger.info("No eo:bands information found")
    
    # Extract JS visualization info explicitly
    logger.info("=== JS VISUALIZATION INFO ===")
    if isinstance(dataset, dict) and 'js_visualization_info' in dataset:
        js_info = dataset['js_visualization_info']
        logger.info(f"Found JS visualization info: {js_info}")
        
        # Log temporal filter info specifically
        if 'temporal_filter' in js_info:
            tf = js_info['temporal_filter']
            logger.info(f"Temporal filter found: {tf}")
            logger.info(f"  Start date: {tf.get('start_date', 'Not specified')}")
            logger.info(f"  End date: {tf.get('end_date', 'Not specified')}")
            logger.info(f"  Filter method: {tf.get('filter_method', 'Not specified')}")
            logger.info(f"  Start param raw: {tf.get('start_param_raw', 'Not specified')}")
            logger.info(f"  End param raw: {tf.get('end_param_raw', 'Not specified')}")
    else:
        logger.info("No JS visualization info found")
    
    # Extract visualization parameters from function
    vis_params, bands, palette, class_descriptions = extract_visualization_params(dataset)
    
    logger.info("=== EXTRACTED VISUALIZATION PARAMETERS ===")
    logger.info(f"Extracted Bands: {bands}")
    logger.info(f"Extracted Palette: {palette}")
    logger.info(f"Extracted Min: {vis_params.get('min', 0)}")
    logger.info(f"Extracted Max: {vis_params.get('max', 3000)}")
    logger.info(f"Extracted Class Descriptions: {class_descriptions}")
    
    # Check additional properties that might be relevant
    logger.info("=== ADDITIONAL PROPERTIES ===")
    if 'properties' in dataset:
        for key, value in dataset['properties'].items():
            if 'vis' in key.lower() or 'band' in key.lower() or 'palette' in key.lower():
                logger.info(f"Property {key}: {value}")
    
    logger.info("==== END DEBUGGING VISUALIZATION PARAMS ====")
    
def process_feature_collection(gee_collection, vis_params, limit_features, skip_confidence_filter):
    """Process a feature collection dataset"""
    logger.info(f"Processing FeatureCollection: {gee_collection}")
    
    try:
        features = ee.FeatureCollection(gee_collection)
        logger.info("Successfully created FeatureCollection reference")
    except Exception as e:
        logger.error(f"Error creating FeatureCollection: {str(e)}")
        raise RuntimeError(f"Failed to create FeatureCollection reference: {str(e)}")
    
    # For the open buildings dataset specifically, we need special handling
    if 'open-buildings' in gee_collection:
        logger.info("Detected Open Buildings dataset, applying special handling")
        try:
            features = filter_open_buildings(
                features, 
                skip_confidence_filter=skip_confidence_filter, 
                limit=limit_features
            )
        except Exception as e:
            logger.error(f"Error filtering Open Buildings: {str(e)}")
            raise
    
    # Create an image from the features for visualization
    try:
        image, updated_vis_params = create_feature_collection_image(features, gee_collection, vis_params)
        map_id_dict = image.getMapId(updated_vis_params)
        return map_id_dict, features, True  # is_feature_collection=True
    except Exception as e:
        logger.error(f"Error generating map tiles for features: {str(e)}")
        raise
    
def process_image(gee_collection, vis_params):
    """Process a single image dataset"""
    logger.info(f"Processing Image: {gee_collection}")
    
    try:
        image = ee.Image(gee_collection)
        
        # Auto-detect RGB visualization if we have 3 bands but no palette
        if 'bands' in vis_params and len(vis_params['bands']) == 3 and 'palette' not in vis_params:
            logger.info(f"Detected potential RGB bands for image: {vis_params['bands']}")
            # Create a copy of vis_params without modifying the original
            rgb_vis_params = vis_params.copy()
            
            # Set appropriate visualization for RGB
            # Remove any potential min/max values that might be inappropriate for RGB
            if 'min' in rgb_vis_params:
                rgb_vis_params['min'] = [rgb_vis_params['min']] * 3 if not isinstance(rgb_vis_params['min'], list) else rgb_vis_params['min']
            else:
                rgb_vis_params['min'] = [0, 0, 0]
                
            if 'max' in rgb_vis_params:
                rgb_vis_params['max'] = [rgb_vis_params['max']] * 3 if not isinstance(rgb_vis_params['max'], list) else rgb_vis_params['max']
            else:
                # Use 255 as the default max for RGB visualization (common for 8-bit imagery like Landsat)
                rgb_vis_params['max'] = [255, 255, 255]
            
            logger.info(f"Using RGB visualization with params: {rgb_vis_params}")
            map_id_dict = image.getMapId(rgb_vis_params)
        else:
            map_id_dict = image.getMapId(vis_params)
            
        return map_id_dict, None, False  # is_feature_collection=False
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise
    
def process_image_collection(gee_collection, date_range, vis_params, dataset=None, point=None):
    """Process an image collection dataset with optimized temporal filtering
    
    Args:
        gee_collection: The GEE collection ID
        date_range: Date range to filter by [start_date, end_date]
        vis_params: Visualization parameters
        dataset: Optional dataset metadata for additional visualization params
        point: Optional ee.Geometry.Point for location-based filtering
        
    Returns:
        tuple: (map_id_dict, features, is_feature_collection)
    """
    logger.info(f"Processing ImageCollection: {gee_collection}")
    
    try:
        # Initialize the collection reference
        collection = ee.ImageCollection(gee_collection)
        
        # Check if we have JS-derived visualization info
        js_info = None
        if dataset and isinstance(dataset, dict) and 'js_visualization_info' in dataset:
            js_info = dataset['js_visualization_info']
            logger.info(f"Found JS visualization info for {gee_collection}")
        
        # Default image variable that will be set by one of the methods below
        image = None
        
        # Special case handlers for specific dataset types
        if 'ESA/WorldCover' in gee_collection:
            logger.info(f"Detected ESA WorldCover dataset, applying special visualization")
            image, updated_vis_params = handle_worldcover_visualization(gee_collection)
            map_id_dict = image.getMapId(updated_vis_params)
            return map_id_dict, None, False
        
        # Special handler for Sentinel-1 SAR GRD data to fix the polarization issue
        if 'COPERNICUS/S1_GRD' in gee_collection:
            logger.info(f"Detected Sentinel-1 GRD dataset, applying special polarization filtering")
            image, updated_vis_params = handle_sentinel1_visualization(gee_collection, date_range, point)
            map_id_dict = image.getMapId(updated_vis_params)
            return map_id_dict, None, False
        
        if 'GOOGLE/Research/open-buildings-temporal/v1' in gee_collection:
            logger.info(f"Detected Open Buildings Temporal dataset, applying special visualization")
            image, updated_vis_params = handle_open_buildings_temporal_visualization(gee_collection, point)
            map_id_dict = image.getMapId(updated_vis_params)
            return map_id_dict, None, False
        
        # Extract and apply temporal filtering information
        # First priority: Check JS visualization info for temporal filter
        if js_info and 'temporal_filter' in js_info:
            # Extract temporal filter information
            tf = js_info['temporal_filter']
            start_date = tf.get('start_date')
            end_date = tf.get('end_date')
            filter_method = tf.get('filter_method', 'filterDate')
            
            logger.info(f"Using temporal filter from JS info")
            logger.info(f"  Filter dates: {start_date} to {end_date}")
            logger.info(f"  Filter method: {filter_method}")
            
            # Apply temporal filtering
            filtered_collection = collection.filterDate(start_date, end_date)
            
            # Check for visualization method in JS info
            visualization_method = js_info.get('visualization_method', '')
            
            if visualization_method == 'first':
                # Use first() method as indicated in the JS example
                logger.info(f"Using 'first' method based on JS example")
                image = collection.first()
            else:
                # Determine best strategy based on dataset type
                # For MODIS and most time-series datasets, selecting the most recent image
                # is often better than creating a mosaic
                is_time_series = True  # Default assumption for most datasets
                
                # Datasets that specifically need mosaics (spatial composites)
                mosaic_datasets = [
                    'LANDSAT', 'COPERNICUS', 'USGS', 'NASA_USDA', 
                    'JAXA', 'ESA', 'UMD', 'TIGER', 'NOAA'
                ]
                
                # Check if this is a dataset that typically needs mosaics
                needs_mosaic = any(dataset_type in gee_collection for dataset_type in mosaic_datasets)
                
                if needs_mosaic or not is_time_series:
                    # Create a mosaic for datasets that need spatial compositing
                    logger.info(f"Creating mosaic for spatial dataset")
                    image = filtered_collection.mosaic()
                else:
                    # For time series data, get most recent image
                    logger.info(f"Using most recent image for time series dataset")
                    image = filtered_collection.sort('system:time_start', False).first()
        else:
            # Second priority: Use date range from metadata
            logger.info(f"Using date range from metadata: {date_range}")
            filtered_collection = collection.filterDate(date_range[0], date_range[1])
            
            # Check if we need to apply median aggregation (for temporal selection)
            aggregation_method = None
            if isinstance(vis_params, dict) and 'temporal_filter' in vis_params:
                aggregation_method = vis_params['temporal_filter'].get('aggregation')
            
            # For most datasets, especially time-series like MODIS, selecting
            # the most recent image often provides better performance and visualization
            is_modis = 'MODIS' in gee_collection
            is_time_series = is_modis or any(x in gee_collection for x in ['VIIRS', 'GOES', 'GLDAS', 'GRIDMET'])
            is_satellite_imagery = any(x in gee_collection for x in ['LANDSAT', 'SENTINEL', 'COPERNICUS'])
            
            # If an aggregation method is specified, apply it
            if aggregation_method == 'median':
                logger.info(f"Applying median aggregation for temporal selection")
                image = filtered_collection.median()
            elif aggregation_method == 'mean':
                logger.info(f"Applying mean aggregation for temporal selection")
                image = filtered_collection.mean()
            elif is_time_series:
                # For time series datasets, use most recent image
                logger.info(f"Using most recent image for time series dataset")
                image = filtered_collection.sort('system:time_start', False).first()
            elif is_satellite_imagery:
                # For satellite imagery, a median composite often looks better
                logger.info(f"Creating median composite for satellite imagery")
                image = filtered_collection.median()
            else:
                # For spatial datasets, create a mosaic
                logger.info(f"Creating mosaic for spatial dataset")
                image = filtered_collection.mosaic()
        
        # If image is still not set, use a fallback approach
        if image is None:
            logger.warning(f"No image created by specialized handlers, using fallback")
            image = filtered_collection.first() or collection.first()
        
        # Apply JS-derived visualization parameters if available
        if js_info:
            # Override vis_params with JS-derived params if available
            if 'vis_bands' in js_info:
                vis_params['bands'] = js_info['vis_bands']
                logger.info(f"Using bands from JS example: {js_info['vis_bands']}")
                
            if 'vis_min' in js_info and 'vis_max' in js_info:
                vis_params['min'] = js_info['vis_min']
                vis_params['max'] = js_info['vis_max']
                logger.info(f"Using min/max from JS example: {js_info['vis_min']}/{js_info['vis_max']}")
                
            if 'vis_palette' in js_info:
                vis_params['palette'] = js_info['vis_palette']
                logger.info(f"Using palette from JS example: {js_info['vis_palette']}")
            
            # If JS example uses specific bands via select() but not in vis_params
            if 'selected_bands' in js_info and 'bands' not in vis_params:
                vis_params['bands'] = js_info['selected_bands']
                logger.info(f"Using selected bands from JS example: {js_info['selected_bands']}")
        
        # For custom band visualization, select the specific band if provided
        if isinstance(vis_params, dict) and 'band' in vis_params:
            selected_band = vis_params['band']
            logger.info(f"Selecting specific band for visualization: {selected_band}")
            
            # Select only the requested band
            if isinstance(selected_band, str):
                image = image.select(selected_band)
                logger.info(f"Visualizing single band: {selected_band}")
        
        # Auto-detect RGB visualization if we have 3 bands but no palette
        if 'bands' in vis_params and len(vis_params['bands']) == 3 and 'palette' not in vis_params:
            logger.info(f"Detected potential RGB bands: {vis_params['bands']}")
            # Create a copy of vis_params without modifying the original
            rgb_vis_params = vis_params.copy()
            
            # Set appropriate visualization for RGB
            if 'min' in rgb_vis_params:
                rgb_vis_params['min'] = [rgb_vis_params['min']] * 3 if not isinstance(rgb_vis_params['min'], list) else rgb_vis_params['min']
            else:
                rgb_vis_params['min'] = [0, 0, 0]
                
            if 'max' in rgb_vis_params:
                rgb_vis_params['max'] = [rgb_vis_params['max']] * 3 if not isinstance(rgb_vis_params['max'], list) else rgb_vis_params['max']
            else:
                rgb_vis_params['max'] = [255, 255, 255]
            
            logger.info(f"Using RGB visualization with params: {rgb_vis_params}")
            map_id_dict = image.getMapId(rgb_vis_params)
        else:
            map_id_dict = image.getMapId(vis_params)
        
        return map_id_dict, None, False  # is_feature_collection=False
    except Exception as e:
        logger.error(f"Error processing image collection: {str(e)}")
        raise