import ee
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def add_surface_water(geometry):
    """Add Global Surface Water visualization."""
    try:
        # Load the Global Surface Water dataset
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')

        # Get the water occurrence layer
        water_occurrence = gsw.select('occurrence')

        # Define visualization parameters here
        vis_params = {
            'min': 0,
            'max': 100,
            'palette': [
                '#ffffff',  # white for no water
                '#d4e7ff',  # very light blue
                '#a8d1ff',  # light blue
                '#7cbaff',  # medium-light blue
                '#51a3ff',  # medium blue
                '#258cff',  # medium-dark blue
                '#0075ff',  # dark blue
                '#005ebf',  # very dark blue
                '#004080'   # darkest blue for permanent water
            ]
        }

        return water_occurrence, vis_params
    except Exception as e:
        logging.error(f"Error in add_surface_water: {e}")
        return None, None