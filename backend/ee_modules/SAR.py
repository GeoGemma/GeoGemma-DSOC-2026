# ee_modules/sar.py
import ee
import logging
import datetime
from typing import Tuple, Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Existing SAR Visualization Function (Keep as is or remove if not needed) ---
DATASET_START_DATE_VIZ = datetime.datetime(2014, 10, 3)
DATASET_END_DATE_VIZ = datetime.datetime(2026, 12, 25) # Approximate

def add_sar_imagery(geometry: ee.Geometry, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """
    Visualizes Sentinel-1 SAR data using temporal filters (spring, late spring, summer).
    Provides range checking. (This is for visualization, not flood mapping analysis).
    """
    try:
        # Check date range
        if start_date_str is None or end_date_str is None:
            start_date = DATASET_START_DATE_VIZ
            end_date = DATASET_END_DATE_VIZ
            logging.info("No Dates Selected for SAR Viz, using full range by default.")
        else:
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                logging.error("Invalid date format for SAR Viz. Use YYYY-MM-DD.")
                return None, {"Status": "Error: Invalid date format. Use YYYY-MM-DD."}

        if start_date < DATASET_START_DATE_VIZ or end_date > DATASET_END_DATE_VIZ:
            data_start_str = DATASET_START_DATE_VIZ.strftime('%Y-%m-%d')
            data_end_str = DATASET_END_DATE_VIZ.strftime('%Y-%m-%d')
            logging.warning("Date out of range for SAR Viz. Sentinel-1 data is available from {} to {}.".format(data_start_str, data_end_str))
            return None, {"Status": "Date out of range. Sentinel-1 data is available from {} to {}.".format(data_start_str, data_end_str)}

        # Sentinel-1 preprocessing steps for visualization
        imgVV = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterDate(start_date, end_date) \
            .filterBounds(geometry) \
            .select('VV') \
            .map(lambda image: image.updateMask(image.mask().And(image.lt(-30.0).Not()))) # Basic noise mask

        desc = imgVV.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
        asc = imgVV.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))

        # Define temporal filters for visualization (Example uses 2024, adjust if needed)
        # Note: These dates might not be relevant if start/end dates are provided
        target_year = start_date.year if start_date else 2024
        spring = ee.Filter.date(datetime.datetime(target_year, 3, 1), datetime.datetime(target_year, 4, 20))
        lateSpring = ee.Filter.date(datetime.datetime(target_year, 4, 21), datetime.datetime(target_year, 6, 10))
        summer = ee.Filter.date(datetime.datetime(target_year, 6, 11), datetime.datetime(target_year, 8, 31))

        # Concatenate the images
        descChange = ee.Image.cat(
            desc.filter(spring).mean(),
            desc.filter(lateSpring).mean(),
            desc.filter(summer).mean())

        ascChange = ee.Image.cat(
            asc.filter(spring).mean(),
            asc.filter(lateSpring).mean(),
            asc.filter(summer).mean())

        # Define visualization parameters
        vis_params = {'min': -25, 'max': 5} # Suitable for RGB composite visualization

        # Return ascending change by default for visualization
        return ascChange, vis_params

    except Exception as e:
        logging.error(f"Error in add_sar_imagery (visualization): {e}", exc_info=True)
        return None, {"Status": f"Error during SAR visualization: {e}"}

# --- NEW FLOOD MAPPING FUNCTION ---

def _otsu(histogram: ee.Dictionary) -> ee.Number:
    """
    Computes the Otsu threshold from a histogram dictionary (EE Python version).

    Args:
        histogram: An ee.Dictionary histogram (e.g., from ee.Reducer.histogram()).
                   Expected keys: 'histogram', 'bucketMeans'.

    Returns:
        The Otsu threshold value (ee.Number).
    """
    # Ensure histogram is a dictionary
    histogram = ee.Dictionary(histogram)

    # Extract relevant values into arrays
    counts = ee.Array(histogram.get('histogram'))
    means = ee.Array(histogram.get('bucketMeans'))

    # Calculate single statistics over arrays
    size = means.length().get([0])
    total = counts.reduce(ee.Reducer.sum(), [0]).get([0])
    sum_val = means.multiply(counts).reduce(ee.Reducer.sum(), [0]).get([0])
    mean_val = sum_val.divide(total)

    # Compute between sum of squares (BSS) for each possible threshold
    indices = ee.List.sequence(1, size)

    # Define a function to compute BSS for a given index i
    def compute_bss(i):
        i = ee.Number(i) # Ensure i is treated as a number
        a_counts = counts.slice(axis=0, start=0, end=i) # Get counts for class A
        a_count = a_counts.reduce(ee.Reducer.sum(), [0]).get([0])

        a_means = means.slice(axis=0, start=0, end=i) # Get means for class A
        # Calculate mean for class A
        a_mean = a_means.multiply(a_counts).reduce(ee.Reducer.sum(), [0]).get([0]).divide(a_count)

        b_count = total.subtract(a_count) # Get count for class B
        # Calculate mean for class B
        b_mean = sum_val.subtract(a_count.multiply(a_mean)).divide(b_count)

        # Compute BSS component for this index
        return a_count.multiply(a_mean.subtract(mean_val).pow(2)).add(
               b_count.multiply(b_mean.subtract(mean_val).pow(2)))

    # Map the BSS computation over all possible indices
    bss = indices.map(compute_bss)

    # Return the mean value corresponding to the maximum BSS
    # Sort means by BSS values in ascending order, get the last one (max BSS)
    return ee.Number(means.sort(bss).get([-1]))


def add_sar_flood_map(geometry: ee.Geometry, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """
    Generates a flood extent map using Sentinel-1 SAR data and Otsu thresholding.

    Args:
        geometry: The region of interest (ee.Geometry).
        start_date_str: Start date (YYYY-MM-DD). If None, searches latest available.
        end_date_str: End date (YYYY-MM-DD). If None alongside start_date_str, searches latest.

    Returns:
        A tuple: (ee.Image, vis_params) for the flood map, or (None, None) on error.
        The returned image is a binary mask (1=water, 0=no water/masked).
    """
    try:
        logging.info(f"Initiating SAR Flood Map for geometry type: {geometry.getInfo()['type']}")

        s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterBounds(geometry)

        target_image = None

        if start_date_str and end_date_str:
            logging.info(f"Using provided date range: {start_date_str} to {end_date_str}")
            # Filter by date and create a median composite for the period
            s1_collection = s1_collection.filterDate(start_date_str, end_date_str)
            collection_size = s1_collection.size().getInfo()
            if collection_size == 0:
                 logging.warning(f"No Sentinel-1 images found for the range {start_date_str} to {end_date_str}")
                 return None, {"Status": f"No Sentinel-1 images found for range {start_date_str} to {end_date_str}"}
            logging.info(f"Found {collection_size} images in range. Creating median composite.")
            target_image = s1_collection.median().select('VV') # Use median for robustness
        else:
            logging.info("No specific date range provided. Searching for the latest available Sentinel-1 image.")
            # Default search window: last 60 days
            today = datetime.date.today()
            search_start = (today - datetime.timedelta(days=60)).strftime('%Y-%m-%d')
            search_end = today.strftime('%Y-%m-%d')
            s1_collection = s1_collection.filterDate(search_start, search_end)

            collection_size = s1_collection.size().getInfo()
            if collection_size == 0:
                logging.warning(f"No Sentinel-1 images found in the last 60 days ({search_start} to {search_end}). Extending search to 120 days.")
                search_start = (today - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
                s1_collection = s1_collection.filterDate(search_start, search_end)
                collection_size = s1_collection.size().getInfo()

                if collection_size == 0:
                    logging.error(f"No Sentinel-1 images found even in the last 120 days ({search_start} to {search_end}).")
                    return None, {"Status": "No recent Sentinel-1 images found (last 120 days)"}

            logging.info(f"Found {collection_size} images in search window. Using the most recent.")
            # Get the most recent image
            target_image = s1_collection.sort('system:time_start', False).first().select('VV')
            img_date = ee.Date(target_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            logging.info(f"Using image from date: {img_date}")

        if target_image is None:
            logging.error("Failed to obtain a target Sentinel-1 image.")
            return None, {"Status": "Failed to obtain target Sentinel-1 image"}

        # --- Otsu Thresholding ---
        logging.info("Calculating histogram for Otsu thresholding...")
        # Define a reducer to calculate a histogram of VV values.
        histogram_reducer = ee.Reducer.histogram(maxBuckets=255, minBucketWidth=0.1)

        # Reduce the VV band values within the geometry. Adjust scale for performance/detail.
        # Scale 30m is a compromise. Native S1 is ~10m but might timeout.
        vv_histogram = target_image.reduceRegion(
            reducer=histogram_reducer,
            geometry=geometry, # Use the input geometry
            scale=30,          # Scale in meters
            maxPixels=1e10,    # Increase maxPixels
            bestEffort=True    # Allow adjusting scale if needed
        ).get('VV') # Get the histogram for the 'VV' band

        # Check if histogram calculation was successful
        if vv_histogram is None:
             logging.error("Histogram calculation failed (result was null). Maybe no valid pixels in the region?")
             return None, {"Status": "Histogram calculation failed (no valid pixels?)"}
        vv_histogram = ee.Dictionary(vv_histogram) # Cast to Dictionary

        # Apply Otsu's method
        logging.info("Applying Otsu thresholding...")
        try:
            otsu_threshold = _otsu(vv_histogram)
            threshold_value = otsu_threshold.getInfo() # Get the value for logging
            logging.info(f"Calculated Otsu threshold: {threshold_value}")
        except Exception as otsu_e:
            logging.error(f"Error during Otsu calculation: {otsu_e}", exc_info=True)
            return None, {"Status": f"Otsu threshold calculation failed: {otsu_e}"}


        # Apply the threshold to create the water mask
        # Water typically has low backscatter (darker in SAR VV), so use less than (<) threshold
        water_mask = target_image.lt(otsu_threshold) # Pixels < threshold are potential water

        # --- Visualization ---
        # Mask non-water pixels (values of 0) and style water as blue
        water_vis = water_mask.selfMask()
        vis_params = {
            'palette': '0000FF' # Solid blue for water
        }
        logging.info("SAR Flood Map processing complete.")

        # Add threshold value to properties for potential metadata extraction later
        water_vis = water_vis.set('otsu_threshold_vv', threshold_value)
        if 'img_date' in locals():
             water_vis = water_vis.set('image_date', img_date)

        return water_vis, vis_params

    except ee.EEException as e:
        logging.error(f"Earth Engine error in add_sar_flood_map: {e}")
        return None, {"Status": f"Earth Engine Error: {e}"}
    except Exception as e:
        logging.error(f"Unexpected error in add_sar_flood_map: {e}", exc_info=True)
        return None, {"Status": f"Unexpected Error: {e}"}