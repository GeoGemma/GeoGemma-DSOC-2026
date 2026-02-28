# ee_modules/forest_change.py
import ee
import logging
from typing import Tuple, Optional, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_tree_cover(geometry: ee.Geometry) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """Adds tree cover layer from the Hansen Global Forest Change dataset."""
    try:
        dataset = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
        treeCover = dataset.select('treecover2000')
        visParams = {
            'bands': ['treecover2000'],
            'min': 0,
            'max': 100,
            'palette': ['black', 'green']
        }
        return treeCover, visParams
    except Exception as e:
        logging.error(f"Error in add_tree_cover: {e}", exc_info=True)
        return None, None

def add_forest_loss(geometry: ee.Geometry) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """Adds forest loss layer from the Hansen Global Forest Change dataset."""
    try:
        dataset = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
        loss = dataset.select('lossyear')
        visParams = {
            'bands': ['lossyear'],
            'min': 0,
            'max': 23,
            'palette': ['yellow', 'red']
        }
        return loss, visParams
    except Exception as e:
        logging.error(f"Error in add_forest_loss: {e}", exc_info=True)
        return None, None

def add_forest_gain(geometry: ee.Geometry) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """Adds forest gain layer from the Hansen Global Forest Change dataset."""
    try:
        dataset = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
        gain = dataset.select('gain')
        gainMasked = gain.updateMask(gain)  # Make 0 values transparent
        visParams = {
            'bands': ['gain'],
            'min': 0,
            'max': 1,
            'palette': ['blue']
        }
        return gainMasked, visParams
    except Exception as e:
        logging.error(f"Error in add_forest_gain: {e}", exc_info=True)
        return None, None