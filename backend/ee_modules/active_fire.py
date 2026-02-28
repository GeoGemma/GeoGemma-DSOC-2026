# --- START OF FILE ee_modules/active_fire.py ---
import ee
import logging
import datetime
from typing import Tuple, Optional, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default time window for searching "latest" active fires (e.g., last 7 days)
DEFAULT_LATEST_WINDOW_DAYS = 7

def add_burn_severity(geometry: ee.Geometry, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """
    Visualizes active fire intensity based on FIRMS T21 brightness temperature.
    Note: This currently shows active fire intensity, not true dNBR burn severity.
    Handles date ranges and 'latest' keyword.

    Args:
        geometry: The region of interest (ee.Geometry).
        start_date_str: Start date (YYYY-MM-DD) or 'latest'.
        end_date_str: End date (YYYY-MM-DD).

    Returns:
        A tuple: (ee.Image, vis_params) for the fire intensity map, or (None, None) on error.
    """
    try:
        # NOTE: The function name 'add_burn_severity' is kept for now,
        # but the module name change addresses the core request.
        # Consider renaming the function later if desired (e.g., to add_active_fires).
        logging.info(f"Processing Active Fire (FIRMS T21) for dates: {start_date_str} to {end_date_str}")

        # --- Date Handling ---
        if start_date_str == "latest":
            logging.info(f"Latest data requested. Using last {DEFAULT_LATEST_WINDOW_DAYS} days.")
            today = datetime.date.today()
            end_date = today.strftime('%Y-%m-%d')
            start_date = (today - datetime.timedelta(days=DEFAULT_LATEST_WINDOW_DAYS)).strftime('%Y-%m-%d')
        elif start_date_str and end_date_str:
            try:
                # Validate input dates
                datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
                datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
                start_date = start_date_str
                end_date = end_date_str
            except ValueError:
                logging.error(f"Invalid date format provided: {start_date_str}, {end_date_str}. Use YYYY-MM-DD.")
                # Fallback to default 'latest' behavior
                today = datetime.date.today()
                end_date = today.strftime('%Y-%m-%d')
                start_date = (today - datetime.timedelta(days=DEFAULT_LATEST_WINDOW_DAYS)).strftime('%Y-%m-%d')
                logging.warning(f"Falling back to latest {DEFAULT_LATEST_WINDOW_DAYS} days due to invalid date format.")
        else:
            # Default to 'latest' if dates are missing or incomplete
            logging.info(f"Incomplete date information. Defaulting to latest {DEFAULT_LATEST_WINDOW_DAYS} days.")
            today = datetime.date.today()
            end_date = today.strftime('%Y-%m-%d')
            start_date = (today - datetime.timedelta(days=DEFAULT_LATEST_WINDOW_DAYS)).strftime('%Y-%m-%d')

        logging.info(f"Using date range: {start_date} to {end_date}")

        # --- Earth Engine Processing ---
        dataset = ee.ImageCollection('FIRMS').filterDate(start_date, end_date).filterBounds(geometry)

        # Check if any data exists for the period/region
        collection_size = dataset.size().getInfo()
        if collection_size == 0:
            logging.warning(f"No FIRMS fire data found for the specified period/region: {start_date} to {end_date}")
            # Return None, but include status in metadata simulation if needed later
            return None, {"Status": f"No FIRMS fire data found for {start_date} to {end_date}"}

        # Select the brightness temperature band
        fires = dataset.select('T21')

        # Create an image showing the maximum fire intensity detected during the period
        # Using max() helps visualize the extent/intensity over time better than median/mosaic
        fire_intensity_image = fires.max().rename('Max_T21_Intensity') # Rename for clarity

        # Define visualization parameters (based on JS example)
        vis_params = {
            'min': 325.0,  # Min temperature in Kelvin (potential fire)
            'max': 400.0,  # Max temperature in Kelvin (intense fire)
            'palette': ['red', 'orange', 'yellow'] # Red (cooler) -> Yellow (hotter)
        }

        logging.info("Successfully processed FIRMS active fire data.")
        return fire_intensity_image, vis_params

    except ee.EEException as e:
        logging.error(f"Earth Engine error in add_burn_severity (FIRMS): {e}", exc_info=True)
        return None, {"Status": f"Earth Engine Error: {e}"}
    except Exception as e:
        logging.error(f"Unexpected error in add_burn_severity (FIRMS): {e}", exc_info=True)
        return None, {"Status": f"Unexpected Error: {e}"}
# --- END OF FILE ee_modules/active_fire.py ---