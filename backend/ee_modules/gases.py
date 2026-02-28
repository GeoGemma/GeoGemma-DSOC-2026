# ee_modules/gases.py
import ee
import logging
import datetime
from typing import Tuple, Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define gas properties
GAS_PROPERTIES = {
    'CO': {
        'collection_id': 'COPERNICUS/S5P/OFFL/L3_CO',
        'band': 'CO_column_number_density',
        'vis': {
            'min': 0,
            'max': 0.05, # mol/m^2
            'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
        },
        'unit': 'mol/m²'
    },
    'NO2': {
        'collection_id': 'COPERNICUS/S5P/OFFL/L3_NO2',
        'band': 'tropospheric_NO2_column_number_density',
        'vis': {
            'min': 0,
            'max': 0.0002, # mol/m^2
            'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
        },
        'unit': 'mol/m²'
    },
    'CH4': {
        'collection_id': 'COPERNICUS/S5P/OFFL/L3_CH4',
        'band': 'CH4_column_volume_mixing_ratio_dry_air',
        'vis': {
            'min': 1750,
            'max': 1900, # ppb
            'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
        },
        'unit': 'ppb'
    },
    'SO2': {
        'collection_id': 'COPERNICUS/S5P/OFFL/L3_SO2',
        'band': 'SO2_column_number_density',
        'vis': {
            'min': 0.0,
            'max': 0.0005, # mol/m^2
            'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
        },
        'unit': 'mol/m²'
    }
    # Can add others like O3, AOD later if needed
}

def add_gas_layer(
    geometry: ee.Geometry,
    gas_type: str,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None
) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """
    Generates a map layer for a specific atmospheric gas concentration (CO, NO2, CH4, SO2).

    Args:
        geometry: The region of interest (ee.Geometry).
        gas_type: The gas identifier ('CO', 'NO2', 'CH4', 'SO2').
        start_date_str: Start date (YYYY-MM-DD). Defaults to latest 30 days if None.
        end_date_str: End date (YYYY-MM-DD). Defaults to today if None.

    Returns:
        A tuple: (ee.Image, vis_params) for the gas layer, or (None, status_dict) on error.
    """
    gas_type = gas_type.upper()
    if gas_type not in GAS_PROPERTIES:
        logging.error(f"Invalid gas type specified: {gas_type}")
        return None, {"Status": f"Error: Invalid gas type '{gas_type}'. Valid types: {list(GAS_PROPERTIES.keys())}"}

    props = GAS_PROPERTIES[gas_type]
    collection_id = props['collection_id']
    band_name = props['band']
    vis_params = props['vis']
    unit = props['unit']

    try:
        logging.info(f"Processing {gas_type} for geometry type: {geometry.getInfo()['type']}")

        # --- Date Handling ---
        if start_date_str == 'latest' or start_date_str is None:
            # Default to the last 30 days if 'latest' or no start date
            today = datetime.date.today()
            end_date = today
            start_date = today - datetime.timedelta(days=30)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            logging.info(f"Using default date range (last 30 days): {start_date_str} to {end_date_str}")
        elif end_date_str is None:
            # If start is provided but not end, default end to today
            end_date_str = datetime.date.today().strftime('%Y-%m-%d')
            logging.info(f"End date not provided, using today: {end_date_str}")

        # --- Data Fetching and Processing ---
        collection = ee.ImageCollection(collection_id) \
            .select(band_name) \
            .filterDate(start_date_str, end_date_str) \
            .filterBounds(geometry)

        collection_size = collection.size().getInfo()
        if collection_size == 0:
            logging.warning(f"No {gas_type} images found for the period {start_date_str} to {end_date_str} in the specified region.")
            return None, {"Status": f"No {gas_type} data found for {start_date_str} to {end_date_str}"}

        logging.info(f"Found {collection_size} {gas_type} images. Calculating mean.")

        # Calculate the mean over the period and clip to the geometry
        mean_image = collection.mean().clip(geometry)

        # Set properties for metadata extraction
        mean_image = mean_image.set('gas_type', gas_type)
        mean_image = mean_image.set('unit', unit)
        mean_image = mean_image.set('start_date', start_date_str)
        mean_image = mean_image.set('end_date', end_date_str)
        mean_image = mean_image.set('ee_collection_id', collection_id) # Add collection ID

        logging.info(f"{gas_type} processing complete.")
        return mean_image, vis_params

    except ee.EEException as e:
        logging.error(f"Earth Engine error processing {gas_type}: {e}")
        return None, {"Status": f"Earth Engine Error processing {gas_type}: {e}"}
    except Exception as e:
        logging.error(f"Unexpected error processing {gas_type}: {e}", exc_info=True)
        return None, {"Status": f"Unexpected Error processing {gas_type}: {e}"}