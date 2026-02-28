# --- START OF FILE ee_metadata.py ---
import ee
import logging
from typing import Dict, Any, Optional, Union
import datetime
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function to safely get info (no changes needed here)
def _safe_get_info(ee_obj: Any, default: Any = 'N/A') -> Any:
    """Safely call getInfo() on an Earth Engine object."""
    if ee_obj is None: return default
    try:
        info = ee_obj.getInfo()
        return info if info is not None else default
    except ee.EEException as e:
        if "not found" in str(e).lower() or "property" in str(e).lower(): logging.debug(f"EE property/info not found: {e}")
        elif "user memory limit exceeded" in str(e).lower(): logging.warning(f"EE info skipped due to memory limit: {e}")
        else: logging.warning(f"Could not get EE info: {e}")
        return default
    except Exception as e:
        logging.warning(f"Non-EE error during getInfo: {e}", exc_info=False)
        return default

# Helper to format values for display (no changes needed here)
def _format_value(value: Any) -> Union[str, Dict]:
    if value is None or value == 'N/A': return 'N/A'
    if isinstance(value, ee.ee_date.Date):
        try: return value.format('YYYY-MM-dd').getInfo()
        except Exception as e: logging.warning(f"Failed to format EE Date: {e}"); return 'Invalid Date Object'
    if isinstance(value, datetime.datetime) or isinstance(value, datetime.date): return value.strftime('%Y-%m-%d')
    if isinstance(value, dict):
        formatted_dict = {}
        for k, v in value.items():
             display_key = str(k).split('_')[-1].capitalize() if '_' in str(k) else str(k).capitalize()
             formatted_dict[display_key] = _format_value(v)
        return formatted_dict if formatted_dict else {'Status': 'Empty Dictionary'}
    elif isinstance(value, float):
        if abs(value) > 1000: return f"{value:,.0f}"
        if abs(value) > 10: return f"{value:,.2f}"
        elif abs(value) > 1e-6 or value == 0: return f"{value:.4f}"
        else: return f"{value:.2e}"
    elif isinstance(value, int):
         if abs(value) >= 1000: return f"{value:,}"
         return str(value)
    else: return str(value)


def extract_metadata(
    source_object: Union[ee.Image, ee.ImageCollection],
    geometry: ee.Geometry,
    start_date_input: Optional[str],
    end_date_input: Optional[str],
    processing_type: str,
    stat_band_name: Optional[str] = None # This is the INPUT parameter
) -> Dict[str, Any]:
    """
    Extracts metadata from EE image/collection, handling 'latest' context.
    """
    metadata = {'Status': 'Processing'}

    # --- Add Basic Info ---
    metadata['PROCESSING TYPE'] = processing_type.replace('_', ' ').title()
    metadata['REQUESTED START'] = _format_value(start_date_input) if start_date_input else 'N/A'
    metadata['REQUESTED END'] = _format_value(end_date_input) if end_date_input else 'N/A'

    if source_object is None: metadata['Status'] = 'Metadata Extraction Failed (No source object)'; return metadata
    if geometry is None: metadata['Status'] = 'Metadata Extraction Failed (No geometry)'; return metadata

    is_collection = isinstance(source_object, ee.ImageCollection)
    image_for_props = None
    collection_id_display = 'N/A'
    collection_size = 0
    is_latest_request = (start_date_input == "latest")

    # stat_band_name_original is NOT needed as a separate variable.
    # We can directly use the input parameter `stat_band_name`.

    try:
        # --- Centroid Calculation ---
        try:
             centroid = geometry.centroid(maxError=10)
             coordinates = _safe_get_info(centroid.coordinates(), None)
             if coordinates: metadata['GEOMETRY CENTROID'] = f"Lon: {coordinates[0]:.4f}, Lat: {coordinates[1]:.4f}"
             else: metadata['GEOMETRY CENTROID'] = 'Error calculating centroid'
        except Exception as cent_e:
             logging.warning(f"Could not calculate centroid: {cent_e}")
             metadata['GEOMETRY CENTROID'] = 'Error calculating centroid'

        # --- Source Dataset & Image Properties ---
        if is_collection:
            collection = source_object
            collection_filtered = collection.filterBounds(geometry)
            collection_size = _safe_get_info(collection_filtered.size(), 0)
            metadata['IMAGE COUNT (IN AOI)'] = _format_value(collection_size)
            if collection_size > 0:
                image_for_props = ee.Image(collection_filtered.first())
                prop_id = _safe_get_info(image_for_props.get('system:id'), None)
                if prop_id:
                    parts = prop_id.split('/')
                    id_part_index = -1
                    for i, part in enumerate(reversed(parts)):
                         if re.match(r'^\d{8}T\d{6}', part) or re.match(r'L[CLTE]\d{2}_\w+_\d{8}(_\d{8}_\d{2}_\w{2})?(_LST_median_celsius)?', part) or re.match(r'\d{4}_\d{2}_\d{2}', part) or len(part) > 15:
                              id_part_index = len(parts) - 1 - i
                              break
                    if id_part_index > 0: collection_id_display = '/'.join(parts[:id_part_index])
                    elif len(parts) > 1: collection_id_display = '/'.join(parts[:-1])
                    else: collection_id_display = prop_id
                else:
                     potential_ids = ['system:visualization_0_product_id', 'DATASET_ID', 'product_id']
                     for pid_key in potential_ids:
                         prop_id = _safe_get_info(collection_filtered.get(pid_key), None)
                         if prop_id: collection_id_display = prop_id; break
                     if collection_id_display == 'N/A': collection_id_display = _safe_get_info(collection_filtered.get('system:id'), 'N/A')
            else:
                 metadata['Status'] = 'No suitable images found in source collection for AOI/Date Range'
                 collection_id_display = _safe_get_info(collection.get('system:id'), 'N/A')
                 if not collection_id_display or collection_id_display == 'N/A': collection_id_display = _safe_get_info(collection.name(), 'N/A')
        else:
            image_for_props = source_object
            metadata['IMAGE COUNT (IN AOI)'] = 1
            potential_ids = ['system:id', 'system:visualization_0_product_id', 'DATASET_ID', 'product_id']
            for pid_key in potential_ids:
                 prop_id = _safe_get_info(image_for_props.get(pid_key), None)
                 if prop_id and prop_id != 'N/A': collection_id_display = prop_id; break
            if collection_id_display == 'N/A':
                 bands = _safe_get_info(image_for_props.bandNames(), [])
                 if 'water' in bands and 'occurrence' in bands: collection_id_display = 'JRC/GSW1_*/GlobalSurfaceWater'
                 elif 'classification' in bands and len(bands) == 1: collection_id_display = 'ESA/WorldCover/v*'
                 elif 'built_percentage' in bands: collection_id_display = 'GOOGLE/GLOBAL_HUMAN_SETTLEMENT/BUILT_UP_AREA/*'
                 elif 'confidence' in bands and len(bands) == 1: collection_id_display = 'GOOGLE/Research/open-buildings*'
                 else: collection_id_display = 'Derived/Composite Image'
        metadata['SOURCE DATASET'] = collection_id_display

        # --- Date Information ---
        if image_for_props:
            acq_time_millis = _safe_get_info(image_for_props.get('system:time_start'), None)
            if acq_time_millis:
                try:
                    ee_date = ee.Date(acq_time_millis)
                    actual_acquisition_date = _format_value(ee_date)
                    metadata['IMAGE DATE'] = actual_acquisition_date
                    if is_collection and collection_size > 1 and not is_latest_request: metadata['IMAGE DATE NOTE'] = '(Date of first image in range/composite)'
                    elif is_collection and collection_size == 1: metadata['IMAGE DATE NOTE'] = '(Single image found in range)'
                    elif not is_collection: metadata['IMAGE DATE NOTE'] = '(Image composite date or reference date)'
                except Exception as date_e: logging.warning(f"Could not format acquisition date from system:time_start: {date_e}"); metadata['IMAGE DATE'] = 'Error processing date'
            else:
                 ds_start = _safe_get_info(image_for_props.get('DATE_ACQUIRED'), _safe_get_info(image_for_props.get('ACQUISITION_DATE'), None))
                 ds_end = _safe_get_info(image_for_props.get('DATE_ACQUIRED_END'), None)
                 year_prop = _safe_get_info(image_for_props.get('year'), _safe_get_info(image_for_props.get('YEAR'), None))
                 if ds_start:
                      metadata['DATASET START'] = _format_value(ds_start)
                      if ds_end: metadata['DATASET END'] = _format_value(ds_end); metadata['DATE INFO'] = f"Dataset Period: {_format_value(ds_start)} to {_format_value(ds_end)}"
                      else: metadata['DATE INFO'] = f"Dataset Date: {_format_value(ds_start)}"
                 elif year_prop: metadata['DATASET YEAR'] = _format_value(year_prop); metadata['DATE INFO'] = f"Dataset represents year: {_format_value(year_prop)}"
                 elif _safe_get_info(image_for_props.get('system:valid_time_start'), None):
                      valid_start = _safe_get_info(image_for_props.get('system:valid_time_start'))
                      valid_end = _safe_get_info(image_for_props.get('system:valid_time_end'))
                      metadata['DATASET START'] = _format_value(ee.Date(valid_start)) if isinstance(valid_start, int) else _format_value(valid_start)
                      metadata['DATASET END'] = _format_value(ee.Date(valid_end)) if isinstance(valid_end, int) else _format_value(valid_end)
                      metadata['DATE INFO'] = f"Validity Period: {metadata['DATASET START']} to {metadata['DATASET END']}"
                 else:
                      if is_collection:
                          coll_start = _safe_get_info(collection.get('system:time_start'), None)
                          coll_end = _safe_get_info(collection.get('system:time_end'), None)
                          if coll_start and coll_end: metadata['DATE INFO'] = f"Original Collection Range: {_format_value(ee.Date(coll_start))} to {_format_value(ee.Date(coll_end))}"
                          elif coll_start: metadata['DATE INFO'] = f"Original Collection Start: {_format_value(ee.Date(coll_start))}"
                 if 'DATE INFO' not in metadata and 'DATASET YEAR' not in metadata and 'IMAGE DATE' not in metadata: metadata['DATE INFO'] = 'No standard date properties found'

        # --- Cloud Cover ---
        is_optical = False
        if 'SENTINEL/S2' in collection_id_display.upper() or 'LANDSAT/L' in collection_id_display.upper(): is_optical = True
        if is_optical and image_for_props and processing_type in ['RGB', 'NDVI']:
            cloud_prop_names = ['CLOUDY_PIXEL_PERCENTAGE', 'CLOUD_COVER', 'cloud_cover_percentage', 'CLOUD_COVERAGE_ASSESSMENT']
            for prop in cloud_prop_names:
                 cloud_cover_val = _safe_get_info(image_for_props.get(prop), None)
                 if cloud_cover_val is not None:
                     cloud_cover_str = f"{_format_value(cloud_cover_val)}%"
                     metadata_key = 'CLOUD COVER (IMAGE)'
                     if is_collection and collection_size > 1 and not is_latest_request: metadata_key = 'CLOUD COVER (COMPOSITE/FIRST IMAGE)'
                     elif is_latest_request: metadata_key = 'CLOUD COVER (LATEST IMAGE)'
                     metadata[metadata_key] = cloud_cover_str; break
            if is_collection and collection_size > 1 and not is_latest_request:
                mean_cloud_str = 'N/A'
                for prop in cloud_prop_names:
                    if _safe_get_info(image_for_props.get(prop)) is not None:
                         try:
                            mean_cloud = collection_filtered.aggregate_mean(prop)
                            mean_cloud_val = _safe_get_info(mean_cloud, None)
                            if mean_cloud_val is not None: mean_cloud_str = f"{_format_value(mean_cloud_val)}%"; metadata['MEAN CLOUD COVER (AOI/RANGE)'] = mean_cloud_str; break
                         except Exception as cloud_e: logging.warning(f"Error aggregating cloud cover for '{prop}': {cloud_e}"); continue
                if 'MEAN CLOUD COVER (AOI/RANGE)' not in metadata: metadata['MEAN CLOUD COVER (AOI/RANGE)'] = mean_cloud_str


        # --- Statistics ---
        # Check if stat_band_name was provided. If so, attempt stats.
        if stat_band_name and source_object is not None:
            target_for_stats = None
            source_image_for_stats = None

            if isinstance(source_object, ee.ImageCollection):
                 collection_filtered = source_object.filterBounds(geometry)
                 size = _safe_get_info(collection_filtered.size(), 0)
                 if size > 0: source_image_for_stats = collection_filtered.median(); logging.info(f"Using median composite of collection for stats calculation.")
                 else: logging.warning("Skipping stats: Empty collection after filtering by geometry."); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'No images in AOI' # Use stat_band_name directly here
            elif isinstance(source_object, ee.Image): source_image_for_stats = source_object; logging.info(f"Using single source image for stats calculation.")

            if source_image_for_stats:
                 bands = _safe_get_info(source_image_for_stats.bandNames(), [])
                 target_stat_band = None
                 stat_band_to_select = stat_band_name # Use the potentially updated name

                 if stat_band_name in bands: target_stat_band = source_image_for_stats.select(stat_band_name); logging.info(f"Calculating stats for selected band '{stat_band_name}'.")
                 elif stat_band_name == 'NDVI' and all(b in bands for b in ['NIR', 'Red']): target_stat_band = source_image_for_stats.normalizedDifference(['NIR', 'Red']).rename('NDVI'); stat_band_to_select = 'NDVI'; logging.info("Calculating stats for NDVI (derived from NIR/Red).")
                 elif stat_band_name == 'NDVI' and all(b in bands for b in ['B8', 'B4']): target_stat_band = source_image_for_stats.normalizedDifference(['B8', 'B4']).rename('NDVI'); stat_band_to_select = 'NDVI'; logging.info("Calculating stats for NDVI (derived from B8/B4).")
                 elif stat_band_name == 'LST_Celsius' and 'ST_B10' in bands: target_stat_band = source_image_for_stats.select('ST_B10').subtract(273.15).rename('LST_Celsius'); stat_band_to_select = 'LST_Celsius'; logging.info("Calculating stats for LST_Celsius (derived from ST_B10 Kelvin).")
                 else: logging.warning(f"Stat band '{stat_band_name}' (or its components) not found in image bands used for stats: {bands}."); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'Band not found in source image'; target_stat_band = None # Use stat_band_name directly here

            # Calculate stats if we have a valid target band
            if target_stat_band:
                try:
                    reducer = ee.Reducer.minMax().combine(ee.Reducer.mean(), '', True).combine(ee.Reducer.stdDev(), '', True).combine(ee.Reducer.count(), '', True)
                    stats = target_stat_band.reduceRegion(reducer=reducer,geometry=geometry,scale=100,maxPixels=1e9,bestEffort=True)
                    stats_info = _safe_get_info(stats, {})
                    stats_dict_formatted = {}
                    # Use stat_band_to_select for accessing reducer results
                    min_val = stats_info.get(f'{stat_band_to_select}_min')
                    max_val = stats_info.get(f'{stat_band_to_select}_max')
                    mean_val = stats_info.get(f'{stat_band_to_select}_mean')
                    stdDev_val = stats_info.get(f'{stat_band_to_select}_stdDev')
                    count_val = stats_info.get(f'{stat_band_to_select}_count')
                    if min_val is not None: stats_dict_formatted['Min'] = _format_value(min_val)
                    if max_val is not None: stats_dict_formatted['Max'] = _format_value(max_val)
                    if mean_val is not None: stats_dict_formatted['Mean'] = _format_value(mean_val)
                    if stdDev_val is not None: stats_dict_formatted['Std Dev'] = _format_value(stdDev_val)
                    if count_val is not None: stats_dict_formatted['Pixel Count'] = _format_value(count_val)
                    # Use the original input stat_band_name for the metadata key
                    if stats_dict_formatted: metadata[f'{stat_band_name.upper()} STATS (AOI)'] = stats_dict_formatted; logging.info(f"Successfully computed stats for {stat_band_name}.")
                    else: logging.warning(f"Stats computation for {stat_band_name} resulted in empty/null values."); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'Could not compute valid stats' # Use stat_band_name here
                except ee.EEException as stat_ee_e:
                     err_str = str(stat_ee_e).lower()
                     # Use the original input stat_band_name in error messages
                     if "computation timed out" in err_str: logging.warning(f"EE Computation Error (Timeout) computing stats for {stat_band_name}: {stat_ee_e}"); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'Error: Computation Timeout'
                     elif "memory limit" in err_str or "too many pixels" in err_str: logging.warning(f"EE Computation Error (Memory/Pixels) computing stats for {stat_band_name}: {stat_ee_e}"); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'Error: Computation Memory/Pixel Limit'
                     elif "no valid pixels" in err_str or "dictionary is empty" in err_str: logging.warning(f"No valid pixels found for stats calculation for {stat_band_name}: {stat_ee_e}"); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'No valid pixels in AOI'
                     else: logging.warning(f"EE Error computing stats for {stat_band_name}: {stat_ee_e}"); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'Error computing stats (EE)'
                except Exception as stat_e: logging.warning(f"Unexpected error computing stats for {stat_band_name}: {stat_e}", exc_info=True); metadata[f'{stat_band_name.upper()} STATS (AOI)'] = 'Error computing stats (Unexpected)'


        # --- Final Status ---
        if metadata.get('Status') == 'Processing':
             # Check if stat_band_name was requested AND if its status contains 'Error'
             stats_key = f'{stat_band_name.upper()} STATS (AOI)' if stat_band_name else None
             if stats_key and stats_key in metadata and isinstance(metadata[stats_key], str) and 'Error' in metadata[stats_key]:
                  metadata['Status'] = f'Metadata Processed with Stat Errors ({metadata[stats_key]})'
             else:
                  metadata['Status'] = 'Metadata Processed Successfully'

    except ee.EEException as meta_ee_e: logging.error(f"EE Error during metadata extraction framework: {meta_ee_e}", exc_info=True); metadata['Status'] = f'Metadata Error (EE): {meta_ee_e}'
    except Exception as e: logging.error(f"Unexpected error during metadata extraction framework: {e}", exc_info=True); metadata['Status'] = f'Metadata Error (Unexpected): {type(e).__name__}'

    # --- Final Formatting & Sorting ---
    final_metadata = {}
    for key, value in metadata.items():
        if isinstance(value, dict): final_metadata[key] = value
        else: final_metadata[key] = _format_value(value)
    sorted_metadata = {}
    key_order = ['Status', 'PROCESSING TYPE', 'SOURCE DATASET', 'REQUESTED START', 'REQUESTED END', 'IMAGE DATE', 'IMAGE DATE NOTE', 'DATE INFO', 'DATASET YEAR', 'DATASET START', 'DATASET END','IMAGE COUNT (IN AOI)','CLOUD COVER (LATEST IMAGE)', 'CLOUD COVER (IMAGE)', 'CLOUD COVER (COMPOSITE/FIRST IMAGE)','MEAN CLOUD COVER (AOI/RANGE)','GEOMETRY CENTROID', 'REQUEST_CENTER_LAT', 'REQUEST_CENTER_LON']
    # Add stats keys only if they exist in the final metadata
    stats_keys = [k for k in final_metadata if k.endswith(' STATS (AOI)')]
    key_order.extend(sorted(stats_keys))
    for key in key_order:
        if key in final_metadata: sorted_metadata[key] = final_metadata[key]
    for key, value in final_metadata.items():
        if key not in sorted_metadata: sorted_metadata[key] = value

    return sorted_metadata
# --- END OF FILE ee_metadata.py ---