import ee
import logging
from typing import Tuple, Optional, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_open_buildings(geometry: ee.Geometry) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """
    Fetches, processes, and styles the latest Google Open Buildings Temporal data
    (building height) for the given geometry.

    Args:
        geometry: The region of interest (ee.Geometry).

    Returns:
        A tuple: (ee.Image, vis_params) for the building height data,
               or (None, None) on error or if no data is found.
    """
    try:
        logging.info(f"Processing Open Buildings data for geometry: {geometry.getInfo()['type']}")

        # Load the Open Buildings Temporal dataset
        collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1')

        # Filter the collection by the AOI bounds first
        filtered_col = collection.filterBounds(geometry)

        # Find the most recent image/timestamp within the bounds
        # Sort by time descending, get the first image's timestamp
        latest_image = filtered_col.sort('system:time_start', False).first()

        if latest_image is None:
            logging.warning(f"No Open Buildings images found for the selected geometry.")
            return None, None

        latest_timestamp = latest_image.get('system:time_start')
        latest_year = ee.Date(latest_timestamp).get('year').getInfo() # Get year for logging/naming
        logging.info(f"Found latest Open Buildings data from timestamp: {latest_timestamp.getInfo()} ({latest_year})")

        # Filter the collection to include only images with this exact timestamp
        # and then mosaic them to cover the geometry.
        mosaic = filtered_col.filter(ee.Filter.eq('system:time_start', latest_timestamp)).mosaic()

        # Select the building height band
        building_height = mosaic.select('building_height')

        # Create a mask to show only actual buildings (height > 0)
        height_mask = building_height.gt(0)
        masked_building_height = building_height.updateMask(height_mask)

        # Define visualization parameters for building height
        # Palette: Blue -> Cyan -> Green -> Yellow -> Dark Orange/Red
        height_vis_params = {
            'min': 0,    # Min height (m)
            'max': 30,   # Max height (m) for color stretch (adjust for better contrast if needed)
            'palette': [
                '0000FF', # Blue (low)
                '00FFFF', # Cyan
                '00FF00', # Green
                'FFFF00', # Yellow
                'FF8C00', # Dark Orange
                'FF0000'  # Red (high) - Added for taller buildings if max is increased
            ]
        }

        logging.info("Successfully processed Open Buildings data.")
        # Set a property for potential use later (e.g., in layer name)
        masked_building_height = masked_building_height.set('year', latest_year)

        return masked_building_height, height_vis_params

    except Exception as e:
        logging.exception(f"Error processing Open Buildings data: {e}") # Use exception for stack trace
        return None, None 