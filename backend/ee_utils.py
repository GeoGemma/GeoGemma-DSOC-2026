# --- START OF FILE ee_utils.py ---

import ee
import os
import re
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from ee_modules import rgb, ndvi, water, lulc, lst, openbuildings, forest_change, SAR, active_fire, gases
import google.auth.credentials
from functools import lru_cache
from typing import Dict, Tuple, Optional, List, Union, Any
import datetime
import json
from ee_metadata import extract_metadata # <--- Import extract_metadata

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- geocoding, get_admin_boundary, get_llm_coordinates remain unchanged as they don't directly use project ID ---

@lru_cache(maxsize=128)
def _geocode_location(location: str) -> Optional[Tuple[float, float]]:
    """
    Geocodes a location using Geopy. This part is cached.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.
    """
    try:
        geolocator = Nominatim(user_agent="earth_engine_map_app")
        geocode = geolocator.geocode(location, timeout=10)  # Added timeout
        if geocode:
            return geocode.latitude, geocode.longitude
        else:
            logging.warning(f"No geocoding results found for: {location}")
            return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logging.error(f"Geocoding failed for {location}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error during geocoding for {location}: {e}")
        return None

async def get_admin_boundary(location: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                      latitude: Optional[float] = None, longitude: Optional[float] = None,
                      llm=None, LLM_INITIALIZED=False) -> Optional[ee.Geometry]:
    """
    Geocodes a location and retrieves its administrative boundary.
    Uses provided coordinates, then Geopy (cached), with LLM fallback.

    Returns an ee.Geometry object or None if lookup fails.
    """
    point = None

    # Try provided coordinates first
    if latitude is not None and longitude is not None:
        point = ee.Geometry.Point(longitude, latitude)
        logging.info(f"Using provided coordinates: {latitude}, {longitude}")
    else:
        # Try Geopy (cached)
        geopy_coords = _geocode_location(location)
        if geopy_coords:
            latitude, longitude = geopy_coords
            point = ee.Geometry.Point(longitude, latitude)
            logging.info(f"Using Geopy coordinates: {latitude}, {longitude}")
        else:
            # Fallback to LLM
            logging.warning("No coordinates found with Geopy, attempting LLM-assisted geocoding")
            if llm and LLM_INITIALIZED:
                try:
                    # Properly await the async function
                    llm_coords = await get_llm_coordinates(location, start_date, end_date, llm, LLM_INITIALIZED)
                    
                    if llm_coords:
                        latitude, longitude = llm_coords
                        point = ee.Geometry.Point(longitude, latitude)
                        logging.info(f"LLM provided coordinates: {latitude}, {longitude}")
                    else:
                        logging.warning("LLM could not provide coordinates.")
                        return None
                except Exception as llm_e:
                     logging.error(f"Error calling async get_llm_coordinates: {llm_e}")
                     return None
            else:
                logging.warning("LLM not available for geocoding fallback")
                return None

    if point is None:  # Double-check we have a point
        return None

    try:
        # Load the FAO GAUL administrative boundaries dataset
        # Using a slightly higher resolution dataset for potentially better boundaries
        admin_col_name = 'FAO/GAUL_SIMPLIFIED_500m/2015/level2' # Default level 2
        try:
             admin_col = ee.FeatureCollection(admin_col_name)
             # Find the feature that intersects the point
             feature = admin_col.filterBounds(point).first()
        except ee.EEException as e:
             logging.warning(f"Error accessing {admin_col_name}: {e}. Trying level 1.")
             admin_col_name = 'FAO/GAUL_SIMPLIFIED_500m/2015/level1'
             try:
                 admin_col = ee.FeatureCollection(admin_col_name)
                 feature = admin_col.filterBounds(point).first()
             except ee.EEException as e1:
                 logging.error(f"Error accessing {admin_col_name} as well: {e1}. Falling back to buffer.")
                 feature = None


        # Extract the geometry
        if feature is None:
            logging.warning(f"No admin boundary found for {location} at ({latitude}, {longitude}) using GAUL L2/L1. Using buffer.")
            # Fall back to a buffer around the point
            buffer_distance = 10000  # 10km buffer
            return point.buffer(buffer_distance)

        geometry = feature.geometry()
        logging.info(f"Successfully obtained geometry for {location} using {admin_col_name}")
        return geometry
    except Exception as e:
        logging.error(f"Error retrieving admin boundary: {e}", exc_info=True)
        # Fallback to point buffer if admin boundary lookup fails
        if point is not None:
            buffer_distance = 10000  # 10km buffer
            logging.warning("Falling back to point buffer due to boundary retrieval error.")
            return point.buffer(buffer_distance)
        return None


async def get_llm_coordinates(location: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                              llm=None, LLM_INITIALIZED=False) -> Optional[Tuple[float, float]]:
    """
    Uses the LLM to obtain coordinates for a location.

    Returns a tuple of (latitude, longitude) or None if lookup fails.
    """
    if not llm or not LLM_INITIALIZED:
        logging.error("LLM not initialized, cannot get coordinates")
        return None

    try:
        # Build context-aware prompt
        date_context = ""
        if start_date and end_date:
            date_context = f" for the period between {start_date} and {end_date}"
        elif start_date:
            date_context = f" around the date {start_date}"

        prompt = f"What are the approximate latitude and longitude coordinates for the center of: {location}{date_context}? Respond ONLY with the latitude, comma, longitude (e.g., 34.0522,-118.2437). If you cannot determine coordinates, respond with 'None'."
        logging.info(f"Sending coordinate request to LLM: {prompt}")

        # Get response from LLM
        response = await llm.ainvoke(prompt)
        response = response.strip() # Clean extra whitespace
        logging.info(f"LLM coordinate response: '{response}'")

        # Extract coordinates using regex - more robust
        coords_match = re.search(r"([-+]?\d{1,3}(?:\.\d+)?)\s*,\s*([-+]?\d{1,3}(?:\.\d+)?)", response)
        if coords_match:
            try:
                latitude = float(coords_match.group(1))
                longitude = float(coords_match.group(2))
                # Basic sanity check for coordinate ranges
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    return latitude, longitude
                else:
                    logging.warning(f"LLM returned coordinates outside valid range: {latitude}, {longitude}")
                    return None
            except ValueError:
                logging.error(f"Could not convert LLM response to coordinates: {response}")
                return None
        else:
            if "none" in response.lower():
                logging.warning(f"LLM indicates no coordinates found for: {location}")
            else:
                logging.warning(f"Could not extract coordinates from LLM response: '{response}'")
            return None

    except Exception as e:
        logging.exception(f"Error getting coordinates from LLM: {e}")
        return None


# MODIFIED: Ensure project_id is accepted and USED (though it wasn't directly used here before, it's good practice for clarity)
def get_clipped_tile_url(image: ee.Image, geometry: ee.Geometry, vis_params: Dict, project_id: Optional[str] = None) -> Optional[str]:
    """
    Clips an Earth Engine image to a geometry and returns the tile URL.
    The project_id is implicitly used by ee operations initiated earlier.

    Returns a URL string or None if the operation fails.
    """
    if image is None or geometry is None or vis_params is None:
         logging.error("Missing image, geometry, or vis_params for get_clipped_tile_url.")
         return None
    # project_id isn't directly used in getMapId call itself, but it's good to acknowledge it's required for the EE session context.
    if project_id is None:
        logging.warning("Project ID context might be missing for get_clipped_tile_url call, operations may fail.")

    try:
        # Clip the image to the geometry
        clipped_image = image.clipToCollection(ee.FeatureCollection(geometry)) # Use clipToCollection for robustness

        # Get the Map ID - this requires the EE session to be initialized with a valid project
        map_id = clipped_image.getMapId(vis_params)

        return map_id['tile_fetcher'].url_format

    except ee.EEException as e:
         # More specific EE errors
         if "Parameter 'value' is required" in str(e) or "Invalid JSON" in str(e):
             logging.error(f"Error getting tile URL - likely issue with vis_params or image: {e}")
             logging.error(f"Vis Params: {vis_params}")
             # Attempt to get image info (can be slow)
             try:
                 logging.error(f"Image Info: {image.getInfo()}")
             except Exception as img_info_e:
                 logging.error(f"Could not get image info: {img_info_e}")
         elif "computation timed out" in str(e).lower() or "memory limit" in str(e).lower():
             logging.error(f"EE Computation Error getting tile URL (Timeout/Memory): {e}")
         elif "project" in str(e).lower(): # Catch project specific errors here too
             logging.error(f"EE Project Error getting tile URL (Project: {project_id}): {e}")
         else:
             logging.error(f"Earth Engine error getting clipped tile URL: {e}")
         return None
    except Exception as e:
        logging.error(f"Unexpected error getting clipped tile URL: {e}", exc_info=True)
        return None


# This is the modified process_image function for ee_utils.py
VALID_GAS_TYPES = ['CO', 'NO2', 'CH4', 'SO2']
def process_image(geometry: ee.Geometry, processing_type: str, satellite: Optional[str] = None,
                 start_date: Optional[str] = None, end_date: Optional[str] = None,
                 year: Optional[int] = None) -> Tuple[Optional[ee.Image], Optional[Dict]]:
    """
    Combines image retrieval and visualization parameter selection.
    Handles satellite and date options for all processing types.

    Returns a tuple of (ee.Image, visualization_parameters) or (None, None) if processing fails.
    """
    try:
        # Log input parameters for debugging
        logging.info(f"Processing image: type={processing_type}, satellite={satellite}, dates={start_date} to {end_date}, year={year}")

        image = None
        vis_params = None

        # Normalize processing type for consistent matching
        normalized_processing_type = processing_type.upper()
        
        # Map common variations to supported types
        processing_type_mapping = {
            'WATER': 'SURFACE WATER',
            'SURFACE_WATER': 'SURFACE WATER',
            'BUILDINGS': 'OPEN BUILDINGS',
            'BUILDING': 'OPEN BUILDINGS',
            'LANDCOVER': 'LULC',
            'LAND COVER': 'LULC',
            'LAND USE': 'LULC',
            'TEMPERATURE': 'LST',
            'LAND SURFACE TEMPERATURE': 'LST',
            'FOREST': 'TREE_COVER',
            'FOREST COVER': 'TREE_COVER',
            'TREE COVER': 'TREE_COVER',
            'VEGETATION': 'NDVI',
            'WILDFIRE': 'ACTIVE_FIRE',
            'FIRE': 'ACTIVE_FIRE',
            'BURNED AREAS': 'ACTIVE_FIRE',
            'BURN SEVERITY': 'ACTIVE_FIRE'
        }
        
        # Apply mapping if found
        if normalized_processing_type in processing_type_mapping:
            normalized_processing_type = processing_type_mapping[normalized_processing_type]
            logging.info(f"Mapped processing type '{processing_type}' to '{normalized_processing_type}'")

        # Process based on normalized type
        if normalized_processing_type == 'RGB':
            # Pass year parameter to RGB module for month/year handling
            image, vis_params = rgb.add_rgb_imagery(geometry, satellite, start_date, end_date, year)
        elif normalized_processing_type == 'NDVI':
            logging.info(f"Calling NDVI with dates: {start_date} to {end_date}")
            image, vis_params = ndvi.add_sentinel_ndvi(geometry, start_date, end_date)
        elif normalized_processing_type == 'SURFACE WATER':
            image, vis_params = water.add_surface_water(geometry)
        elif normalized_processing_type == 'LULC':
            image, vis_params = lulc.add_lulc(geometry)
        elif normalized_processing_type == 'LST':
            # Pass both year AND start_date/end_date to LST module
            logging.info(f"Calling LST with geometry, year='{year}', and dates: {start_date} to {end_date}")
            image, vis_params = lst.add_landsat_lst(geometry, year, start_date, end_date)
        elif normalized_processing_type == 'OPEN BUILDINGS':
            image, vis_params = openbuildings.add_open_buildings(geometry)
        elif normalized_processing_type == 'TREE_COVER':
            logging.info("Calling add_tree_cover")
            image, vis_params = forest_change.add_tree_cover(geometry)
        elif normalized_processing_type == 'SAR':
            logging.info("Calling SAR Imagery function")
            image, vis_params = SAR.add_sar_imagery(geometry, start_date, end_date)
        elif normalized_processing_type == 'FLOOD MAPPING':
            logging.info(f"Calling SAR Flood Mapping with dates: {start_date} to {end_date}")
            image, vis_params = SAR.add_sar_flood_map(geometry, start_date, end_date)
        elif normalized_processing_type == 'FOREST_LOSS':
            logging.info("Calling add_forest_loss")
            image, vis_params = forest_change.add_forest_loss(geometry)
        elif normalized_processing_type == 'FOREST_GAIN':
            image, vis_params = forest_change.add_forest_gain(geometry)
        elif normalized_processing_type == 'ACTIVE_FIRE': 
            logging.info(f"Calling Active Fire function with dates: {start_date} to {end_date}")
            image, vis_params = active_fire.add_burn_severity(geometry, start_date, end_date)
        elif normalized_processing_type in VALID_GAS_TYPES:
            logging.info(f"Calling Gas Layer function for {normalized_processing_type} with dates: {start_date} to {end_date}")
            # Pass the specific gas type (e.g., 'CO', 'NO2') as processing_type
            image, vis_params = gases.add_gas_layer(geometry, normalized_processing_type, start_date, end_date)
        else:
            logging.warning(f"Invalid processing type: {processing_type} (normalized: {normalized_processing_type})")
            return None, None

        # Log result status
        if image is None:
            logging.warning(f"No image returned for {normalized_processing_type}")
        elif vis_params is None:
            logging.warning(f"No visualization parameters returned for {normalized_processing_type}")
        else:
             # Basic validation of vis_params
             if not isinstance(vis_params, dict) or 'palette' not in vis_params and 'bands' not in vis_params:
                 logging.warning(f"Potentially invalid vis_params for {normalized_processing_type}: {vis_params}")
             else:
                 logging.info(f"Successfully processed {normalized_processing_type} image")

        return image, vis_params
    except ee.EEException as e:
        logging.error(f"Earth Engine error in process_image for {processing_type}: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error in process_image for {processing_type}: {e}", exc_info=True)
        return None, None


# MODIFIED: Ensure project_id parameter is accepted and passed down correctly
async def get_tile_url(location: str, processing_type: str, project_id: str, satellite: Optional[str] = None,
                start_date: Optional[str] = None, end_date: Optional[str] = None, year: Optional[int] = None,
                latitude: Optional[float] = None, longitude: Optional[float] = None,
                llm=None, LLM_INITIALIZED=False) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Fetches an Earth Engine tile URL and extracts metadata.
    Includes options for satellite, start_date, and end_date for all processing types.
    Uses provided coordinates if available.
    Requires a valid project_id for EE operations.

    Returns a tuple: (URL string, metadata dictionary) or (None, None).
    """
    tile_url = None
    metadata = None
    geometry = None # Initialize geometry

    if not project_id:
         logging.error("get_tile_url requires a project_id.")
         return None, {"Status": "Configuration Error: Project ID missing"}

    try:
        # Get the administrative boundary (doesn't need project_id)
        geometry = await get_admin_boundary(location, start_date, end_date, latitude, longitude, llm, LLM_INITIALIZED)
        if geometry is None:
            logging.warning(f"Could not retrieve administrative boundary for {location}")
            # Return failure status in metadata
            return None, {"Status": f"Failed to get geometry for location: {location}"}

        # Get the Earth Engine image and visualization parameters (implicitly uses initialized EE session with project_id)
        image, vis_params = process_image(geometry, processing_type, satellite, start_date, end_date, year)
        if image is None or vis_params is None:
            logging.warning(f"Could not retrieve image or visualization parameters for {location} and {processing_type}")
            # Return failure status in metadata
            proc_status = f"Failed to process {processing_type} image/vis_params"
            # Try to get basic metadata even if image processing failed, if possible (e.g., if LST year was invalid)
            # This might be difficult; for now, return a simple failure status.
            return None, {"Status": proc_status}

        # --- Metadata Extraction ---
        stat_band_name = None
        if processing_type == 'NDVI':
            stat_band_name = 'NDVI'
        elif processing_type == 'LST':
            stat_band_name = 'LST_Celsius'
        # Add other stat bands if needed

        logging.info(f"Extracting metadata for {processing_type}...")
        # extract_metadata operates on EE objects which depend on the initialized session
        metadata = extract_metadata(
            source_object=image, # Use the retrieved image
            geometry=geometry,
            start_date_input=start_date,
            end_date_input=end_date,
            processing_type=processing_type,
            stat_band_name=stat_band_name
        )
        if metadata:
             logging.info("Metadata extracted successfully.")
             # Add Lat/Lon used for the request to metadata if available
             if latitude and longitude:
                  metadata['REQUEST_CENTER_LAT'] = f"{latitude:.4f}"
                  metadata['REQUEST_CENTER_LON'] = f"{longitude:.4f}"
             # Add geometry centroid if coords weren't passed (moved inside extract_metadata)
        else:
             logging.warning("Metadata extraction failed.")
             metadata = {"Status": "Metadata extraction failed"} # Provide basic error status

        # --- Get Tile URL ---
        logging.info(f"Generating tile URL for {processing_type}...")
        # Pass project_id for clarity/context, even if not directly used by the call signature of get_clipped_tile_url
        tile_url = get_clipped_tile_url(image, geometry, vis_params, project_id)
        if tile_url is None:
            logging.warning(f"Could not generate tile URL for {location} and {processing_type}")
            # Update metadata status if URL fails but metadata succeeded partially
            if metadata and metadata.get("Status", "").startswith("Metadata Processed"):
                 metadata["Status"] = "Metadata Processed, but Tile URL generation failed"
            elif not metadata:
                 metadata = {"Status": "Tile URL generation failed (and metadata failed earlier)"}
            else: # Append to existing error status in metadata
                 metadata["Status"] += "; Tile URL generation failed"
            return None, metadata # Return None URL, but existing/updated metadata

        logging.info(f"Successfully generated tile URL and metadata for {processing_type}")
        return tile_url, metadata

    except ee.EEException as e:
        logging.error(f"Earth Engine error in get_tile_url for {processing_type} (Project: {project_id}): {e}")
        # Try to return any metadata gathered before the error, update status
        err_status = f"EE Error during URL/Metadata generation: {e}"
        if metadata: metadata["Status"] = err_status
        else: metadata = {"Status": err_status}
        return tile_url, metadata # tile_url might be None here
    except Exception as e:
        logging.error(f"Unexpected error in get_tile_url for {processing_type}: {e}", exc_info=True)
        # Try to return any metadata gathered before the error, update status
        err_status = f"Unexpected error during URL/Metadata generation: {type(e).__name__}"
        if metadata: metadata["Status"] = err_status
        else: metadata = {"Status": err_status}
        return tile_url, metadata # tile_url might be None here


# MODIFIED: Ensure project_id parameter is accepted and passed down correctly
def process_time_series(geometry: ee.Geometry, processing_type: str, start_date: str, end_date: str,
                       interval: str = "monthly", project_id: str = None) -> List[Dict[str, Any]]:
    """
    Process a time series of images for a given location and processing type, including metadata.
    Requires a valid project_id for EE operations.

    Args:
        geometry: Earth Engine geometry object
        processing_type: Type of processing (RGB, NDVI, etc.)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Time interval ('daily', 'weekly', 'monthly', 'yearly')
        project_id: GCP project ID (Required)

    Returns:
        List of dictionaries with time series data, URLs, and metadata
    """
    if geometry is None:
         logging.error("Geometry is required for process_time_series")
         return [{"error": "Geometry is required"}]
    if not project_id:
         logging.error("Project ID is required for process_time_series")
         return [{"error": "Configuration Error: Project ID missing"}]

    try:
        # Parse dates
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d')

        # Generate date intervals (logic remains same)
        dates = []
        current_date = start
        delta = None

        if interval == 'daily':
            delta = datetime.timedelta(days=1)
        elif interval == 'weekly':
            delta = datetime.timedelta(days=7)
        elif interval == 'monthly':
            current_date = datetime.datetime(start.year, start.month, 1)
            while current_date <= end:
                month_start = current_date.strftime('%Y-%m-%d')
                # Calculate end of month
                if current_date.month == 12:
                    month_end_dt = datetime.datetime(current_date.year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    month_end_dt = datetime.datetime(current_date.year, current_date.month + 1, 1) - datetime.timedelta(days=1)
                # Ensure end of month doesn't exceed overall end date
                if month_end_dt > end: month_end_dt = end
                month_end = month_end_dt.strftime('%Y-%m-%d')
                dates.append({'start': month_start, 'end': month_end})
                # Move to day after month_end_dt, unless it's already past the overall end date
                if month_end_dt >= end: break
                current_date = month_end_dt + datetime.timedelta(days=1)

        elif interval == 'yearly':
            current_date = datetime.datetime(start.year, 1, 1)
            while current_date.year <= end.year:
                year_start = current_date.strftime('%Y-%m-%d')
                year_end = f"{current_date.year}-12-31"
                # Ensure year_end doesn't exceed the overall end_date
                if datetime.datetime.strptime(year_end, '%Y-%m-%d') > end:
                    year_end = end.strftime('%Y-%m-%d')
                dates.append({'start': year_start, 'end': year_end})
                # Move to next year
                current_date = datetime.datetime(current_date.year + 1, 1, 1)
        else:
            logging.error(f"Invalid interval: {interval}")
            return [{"error": f"Invalid interval: {interval}"}]

        # Handle daily/weekly date generation
        if delta:
            while current_date <= end:
                # For daily/weekly, start and end of interval are the same day
                interval_start_end = current_date.strftime('%Y-%m-%d')
                dates.append({'start': interval_start_end, 'end': interval_start_end})
                current_date += delta

        logging.info(f"Generated {len(dates)} intervals for time series ({interval})")

        # Process each interval and generate time series data
        results = []
        for i, date_info in enumerate(dates):
            interval_start = date_info['start']
            interval_end = date_info['end']
            logging.info(f"Processing time series interval {i+1}/{len(dates)}: {interval_start} to {interval_end}")

            # Extract year for LST processing (use the start year of the interval)
            year = datetime.datetime.strptime(interval_start, '%Y-%m-%d').year if processing_type == 'LST' else None

            # Get image and visualization parameters for the interval (uses EE session context)
            image, vis_params = process_image(geometry, processing_type, None, interval_start, interval_end, year)

            tile_url = None
            metadata = None
            timestep_result = {
                'interval_start': interval_start,
                'interval_end': interval_end,
                'tile_url': None,
                'metadata': None, # Initialize metadata field
                'error': None
            }

            if image is not None and vis_params is not None:
                # --- Metadata Extraction for Timestep ---
                stat_band_name = None
                if processing_type == 'NDVI':
                    stat_band_name = 'NDVI'
                elif processing_type == 'LST':
                    stat_band_name = 'LST_Celsius'

                logging.info(f"Extracting metadata for timestep {interval_start}...")
                # Metadata extraction depends on the EE session context
                metadata = extract_metadata(
                    source_object=image,
                    geometry=geometry,
                    start_date_input=interval_start, # Use interval dates
                    end_date_input=interval_end,
                    processing_type=processing_type,
                    stat_band_name=stat_band_name
                )
                timestep_result['metadata'] = metadata if metadata else {"Status": "Metadata extraction failed for timestep"}

                # --- Get Tile URL for Timestep ---
                logging.info(f"Generating tile URL for timestep {interval_start}...")
                # Pass project_id for clarity/context
                tile_url = get_clipped_tile_url(image, geometry, vis_params, project_id)
                timestep_result['tile_url'] = tile_url

                if tile_url is None:
                    logging.warning(f"Could not generate tile URL for timestep: {interval_start}")
                    timestep_result['error'] = 'Could not generate tile URL for this interval'
                    # Update metadata status if needed
                    if metadata and metadata.get("Status", "").startswith("Metadata Processed"):
                         metadata["Status"] = "Metadata Processed, but Tile URL generation failed"
                    elif not metadata:
                         metadata = {"Status": "Tile URL generation failed (and metadata failed earlier)"}
                    else:
                         metadata["Status"] += "; Tile URL generation failed"
                    timestep_result['metadata'] = metadata # Ensure metadata reflects the URL failure

            else:
                logging.warning(f"Could not process image for interval: {interval_start} to {interval_end}")
                timestep_result['error'] = 'Could not process image for this interval'
                timestep_result['metadata'] = {"Status": "Image processing failed for timestep"}

            results.append(timestep_result)

        return results
    except ee.EEException as e:
        logging.exception(f"Earth Engine error processing time series (Project: {project_id}): {e}")
        return [{"error": f"EE Error: {e}"}]
    except Exception as e:
        logging.exception(f"Unexpected error processing time series: {e}")
        return [{"error": f"Unexpected Error: {e}"}]


# --- Statistics functions are removed as requested (handled by extract_metadata) ---

# --- END OF FILE ee_utils.py ---