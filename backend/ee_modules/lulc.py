import ee
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_lulc(geometry):
    """
    Adds the ESA WorldCover 10m LULC data to the map.

    Args:
        geometry: The region of interest (ee.Geometry).

    Returns:
        A tuple: (ee.Image, vis_params) for the LULC data, or (None, None) on error.
    """
    try:
        # ESA WorldCover 10m v100 is an ImageCollection.  Select the 'Map' band.
        lulc_collection = ee.ImageCollection("ESA/WorldCover/v100")
        lulc = lulc_collection.first().select('Map') # Get the first image and select 'Map'

        # Visualization parameters (taken from the Earth Engine Data Catalog).
        vis_params = {
            'min': 10,
            'max': 95,  # Corrected max value
            'palette': [
                '006400',  # Tree cover
                'ffbb22',  # Shrubland
                'ffff4c',  # Grassland
                'f096ff',  # Cropland
                'fa0000',  # Built-up
                'b4b4b4',  # Bare / sparse vegetation
                'f0f0f0',  # Snow and ice
                '0064c8',  # Permanent water bodies
                '0096a0',  # Herbaceous wetland
                '00cf75',  # Mangroves
                'fae6a0'   # Moss and lichen
            ]
        }

        return lulc, vis_params

    except Exception as e:
        logging.error(f"Error in add_lulc: {e}")
        return None, None