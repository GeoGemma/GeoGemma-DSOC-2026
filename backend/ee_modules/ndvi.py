import ee
import datetime 
import logging
import re
from date_handler import date_handler  # Utilize the date_handler class

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_sentinel_ndvi(geometry, start_date=None, end_date=None):
    """Add Sentinel-2 NDVI visualization with enhanced date handling."""
    try:
        # Normalize date inputs using date_handler
        if start_date == "latest" and end_date == "latest":
            logging.info("Fetching latest NDVI imagery (Sentinel-2)")
            # Set date range to last 90 days for searching the latest image
            today = datetime.date.today()
            search_start = (today - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            search_end = today.strftime('%Y-%m-%d')
            
            # Get Sentinel-2 data
            s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                           .filterBounds(geometry)
                           .filterDate(search_start, search_end)
                           .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
            
            # Check if collection is empty
            collection_size = s2_collection.size().getInfo()
            logging.info(f"Sentinel-2 latest collection search size: {collection_size}")
            
            if collection_size == 0:
                logging.warning("No recent Sentinel-2 images found for 'latest', extending search window")
                # Extend search window to last 180 days if no images found
                search_start = (today - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
                s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                              .filterBounds(geometry)
                              .filterDate(search_start, search_end)
                              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))  # Slightly relaxed cloud filter
                
                collection_size = s2_collection.size().getInfo()
                logging.info(f"Extended Sentinel-2 search (180 days) size: {collection_size}")
                
                if collection_size == 0:
                    logging.warning("No Sentinel-2 images found even with extended search, falling back to Landsat")
                    # Pass "latest" flags to Landsat function
                    return add_landsat_ndvi(geometry, "latest", "latest")
            
            # Get the most recent image
            most_recent = s2_collection.sort('system:time_start', False).first()
            
            # Calculate NDVI
            ndvi = most_recent.normalizedDifference(['B8', 'B4']).rename('NDVI')
            
            # Get the actual acquisition date for logging
            image_date = ee.Date(most_recent.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            logging.info(f"Using most recent Sentinel-2 image from {image_date}")
            
        else:
            # Enhanced handling for specific date ranges
            # Process start_date and end_date using the date_handler
            if start_date is None or end_date is None:
                # Get default 90-day window if dates are missing
                today = datetime.date.today()
                if start_date is None:
                    start_date = (today - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
                if end_date is None:
                    end_date = today.strftime('%Y-%m-%d')
                
                logging.info(f"Adjusted date range for NDVI: {start_date} to {end_date}")
            
            # Try to extract year/month pattern if it's a partial date
            if isinstance(start_date, str) and not re.match(r'^\d{4}-\d{2}-\d{2}$', start_date):
                # Check for year-month format like "2023-04" or "April 2023"
                month, year = date_handler.extract_month_from_prompt(start_date)
                if month and year:
                    # Create a proper date range for the month
                    start_date, end_date = date_handler.get_date_range(None, None, year, month)
                    logging.info(f"Extracted month-year from input: {month}/{year} → range: {start_date} to {end_date}")

            # Check start date to decide which collection to use
            start_year = int(start_date.split('-')[0]) if isinstance(start_date, str) and re.match(r'^\d{4}', start_date) else datetime.datetime.now().year
            
            # Use Sentinel-2 for dates after 2015
            if start_year >= 2015:
                logging.info(f"Using Sentinel-2 for NDVI (Year: {start_year}) for range: {start_date} to {end_date}")
                s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                .filterBounds(geometry)
                                .filterDate(start_date, end_date)
                                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
                
                # Check if collection is empty
                collection_size = s2_collection.size().getInfo()
                logging.info(f"Sentinel-2 collection size: {collection_size}")
                
                if collection_size == 0:
                    # Try with extended date range and relaxed cloud filter
                    # Extend by 30 days in both directions if possible
                    start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                    extended_start = (start_dt - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
                    extended_end = (end_dt + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    logging.warning(f"Empty Sentinel-2 collection, trying extended range: {extended_start} to {extended_end}")
                    s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                   .filterBounds(geometry)
                                   .filterDate(extended_start, extended_end)
                                   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))  # Relaxed cloud filter
                    
                    collection_size = s2_collection.size().getInfo()
                    logging.info(f"Extended Sentinel-2 collection size: {collection_size}")
                    
                    if collection_size == 0:
                        logging.warning(f"Still empty collection after extension, falling back to Landsat")
                        return add_landsat_ndvi(geometry, start_date, end_date)
                
                median_composite = s2_collection.median()
                ndvi = median_composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
                
            else:
                # For dates before 2015, use Landsat
                logging.info(f"Start year {start_year} < 2015, using Landsat for NDVI")
                return add_landsat_ndvi(geometry, start_date, end_date)
        
        # Define visualization parameters
        vis_params = get_ndvi_vis_params()
        
        logging.info("Successfully created Sentinel-2 NDVI visualization")
        return ndvi, vis_params
    except Exception as e:
        logging.error(f"Error in add_sentinel_ndvi: {e}", exc_info=True)
        # Log the dates that caused the error
        logging.error(f"Error occurred with dates: start={start_date}, end={end_date}")
        # Try fallback to Landsat
        try:
            logging.info("Attempting Landsat fallback after Sentinel-2 error")
            return add_landsat_ndvi(geometry, start_date, end_date)
        except Exception as e2:
            logging.error(f"Landsat fallback also failed: {e2}")
            return None, None

def add_landsat_ndvi(geometry, start_date=None, end_date=None):
    """Add Landsat NDVI visualization with enhanced date handling."""
    try:
        # Handle "latest" case
        if start_date == "latest" and end_date == "latest":
            logging.info("Fetching latest Landsat NDVI imagery")
            # Set date range to last 120 days for searching the latest image (extended range)
            today = datetime.date.today()
            search_start = (today - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
            search_end = today.strftime('%Y-%m-%d')
            
            ndvi_image = None  # Initialize variable
            
            # Try Landsat 9 first (newest)
            l9_collection = (ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
                            .filterBounds(geometry)
                            .filterDate(search_start, search_end)
                            .filter(ee.Filter.lt('CLOUD_COVER', 20)))
            
            # Check if L9 collection is empty
            l9_size = l9_collection.size().getInfo()
            logging.info(f"Landsat 9 latest collection search size: {l9_size}")
            
            if l9_size > 0:
                # Process Landsat 9
                l9_collection = l9_collection.map(apply_scale_factors)
                most_recent = l9_collection.sort('system:time_start', False).first()
                ndvi_image = most_recent.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                
                # Get the actual acquisition date for logging
                image_date = ee.Date(most_recent.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                logging.info(f"Using most recent Landsat 9 image from {image_date}")
                
            else:
                # Try Landsat 8 if no L9 data
                l8_collection = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                                .filterBounds(geometry)
                                .filterDate(search_start, search_end)
                                .filter(ee.Filter.lt('CLOUD_COVER', 20)))
                
                # Check if L8 collection is empty
                l8_size = l8_collection.size().getInfo()
                logging.info(f"Landsat 8 latest collection search size: {l8_size}")
                
                if l8_size > 0:
                    # Process Landsat 8
                    l8_collection = l8_collection.map(apply_scale_factors)
                    most_recent = l8_collection.sort('system:time_start', False).first()
                    ndvi_image = most_recent.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                    
                    # Get the actual acquisition date for logging
                    image_date = ee.Date(most_recent.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    logging.info(f"Using most recent Landsat 8 image from {image_date}")
                    
                else:
                    # Try Landsat 7 as last resort with larger window
                    search_start_extended = (today - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
                    l7_collection = (ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
                                    .filterBounds(geometry)
                                    .filterDate(search_start_extended, search_end)
                                    .filter(ee.Filter.lt('CLOUD_COVER', 30)))  # More relaxed cloud filter
                    
                    # Check if L7 collection is empty
                    l7_size = l7_collection.size().getInfo()
                    logging.info(f"Landsat 7 latest collection search size: {l7_size}")
                    
                    if l7_size > 0:
                        # Process Landsat 7
                        l7_collection = l7_collection.map(apply_scale_factors)
                        most_recent = l7_collection.sort('system:time_start', False).first()
                        ndvi_image = most_recent.normalizedDifference(['SR_B4', 'SR_B3']).rename('NDVI')
                        
                        # Get the actual acquisition date for logging
                        image_date = ee.Date(most_recent.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                        logging.info(f"Using most recent Landsat 7 image from {image_date}")
                        
                    else:
                        logging.warning("No recent Landsat imagery found for 'latest'")
                        return None, None
            
            if ndvi_image is None:
                logging.error("Failed to generate NDVI image for 'latest' Landsat.")
                return None, None
                
        else:
            # Handle specific date range with enhanced handling
            if start_date is None or end_date is None:
                today = datetime.date.today()
                if start_date is None:
                    start_date = (today - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
                if end_date is None:
                    end_date = today.strftime('%Y-%m-%d')
                
                logging.info(f"Adjusted date range for Landsat NDVI: {start_date} to {end_date}")
            
            # Try to extract year/month pattern if it's a partial date
            if isinstance(start_date, str) and not re.match(r'^\d{4}-\d{2}-\d{2}$', start_date):
                # Check for year-month format like "2023-04" or "April 2023"
                month, year = date_handler.extract_month_from_prompt(start_date)
                if month and year:
                    # Create a proper date range for the month
                    start_date, end_date = date_handler.get_date_range(None, None, year, month)
                    logging.info(f"Extracted month-year from input: {month}/{year} → range: {start_date} to {end_date}")
            
            start_year = int(start_date.split('-')[0]) if isinstance(start_date, str) and re.match(r'^\d{4}', start_date) else datetime.datetime.now().year
            ndvi_image = None  # Initialize
            
            # Determine which Landsat collection(s) to use based on the date range
            landsat_collections = []
            
            # Landsat 9 (available from late 2021)
            if end_date >= "2021-09-27":
                landsat_collections.append(
                    ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
                        .filterDate(start_date, end_date)
                        .filterBounds(geometry)
                        .filter(ee.Filter.lt('CLOUD_COVER', 20))
                        .map(apply_scale_factors)
                        .select(['SR_B5', 'SR_B4'], ['NIR', 'RED'])
                )
                logging.info("Including Landsat 9 in collection merge.")
            
            # Landsat 8 (available from 2013)
            if start_date < "2022-01-01" and end_date >= "2013-04-11":
                landsat_collections.append(
                    ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                        .filterDate(start_date, end_date)
                        .filterBounds(geometry)
                        .filter(ee.Filter.lt('CLOUD_COVER', 20))
                        .map(apply_scale_factors)
                        .select(['SR_B5', 'SR_B4'], ['NIR', 'RED'])
                )
                logging.info("Including Landsat 8 in collection merge.")
            
            # Landsat 7 (use if range overlaps period before L8/L9 or if L8/L9 is empty)
            if start_date < "2013-04-11":
                landsat_collections.append(
                    ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
                        .filterDate(start_date, end_date)
                        .filterBounds(geometry)
                        .filter(ee.Filter.lt('CLOUD_COVER', 20))
                        .map(apply_scale_factors)
                        .select(['SR_B4', 'SR_B3'], ['NIR', 'RED'])
                )
                logging.info("Including Landsat 7 in collection merge.")
            
            if not landsat_collections:
                logging.warning(f"No suitable Landsat collections found for the date range: {start_date} to {end_date}")
                # Try with extended dates (+/- 30 days) and relaxed cloud filters
                start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                extended_start = (start_dt - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
                extended_end = (end_dt + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
                
                logging.info(f"Trying with extended date range: {extended_start} to {extended_end}")
                
                # Add collections with extended dates and relaxed cloud filter
                if extended_end >= "2021-09-27":
                    landsat_collections.append(
                        ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
                            .filterDate(extended_start, extended_end)
                            .filterBounds(geometry)
                            .filter(ee.Filter.lt('CLOUD_COVER', 30))
                            .map(apply_scale_factors)
                            .select(['SR_B5', 'SR_B4'], ['NIR', 'RED'])
                    )
                
                if extended_start < "2022-01-01" and extended_end >= "2013-04-11":
                    landsat_collections.append(
                        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                            .filterDate(extended_start, extended_end)
                            .filterBounds(geometry)
                            .filter(ee.Filter.lt('CLOUD_COVER', 30))
                            .map(apply_scale_factors)
                            .select(['SR_B5', 'SR_B4'], ['NIR', 'RED'])
                    )
                
                if extended_start < "2013-04-11":
                    landsat_collections.append(
                        ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
                            .filterDate(extended_start, extended_end)
                            .filterBounds(geometry)
                            .filter(ee.Filter.lt('CLOUD_COVER', 30))
                            .map(apply_scale_factors)
                            .select(['SR_B4', 'SR_B3'], ['NIR', 'RED'])
                    )
                
                if not landsat_collections:
                    logging.warning(f"No suitable Landsat collections found even with extended dates")
                    return None, None
            
            # Merge collections if more than one
            if len(landsat_collections) > 1:
                merged_collection = ee.ImageCollection(landsat_collections[0])
                for i in range(1, len(landsat_collections)):
                    merged_collection = merged_collection.merge(landsat_collections[i])
                logging.info(f"Merged {len(landsat_collections)} Landsat collections.")
            else:
                merged_collection = landsat_collections[0]
            
            # Check size of final collection
            collection_size = merged_collection.size().getInfo()
            logging.info(f"Final Landsat collection size: {collection_size}")
            
            if collection_size == 0:
                logging.warning(f"Empty final Landsat collection for {start_date} to {end_date}")
                return None, None
            
            # Calculate median composite and NDVI
            median_composite = merged_collection.median()
            # Calculate NDVI using the consistently named bands 'NIR' and 'RED'
            ndvi_image = median_composite.normalizedDifference(['NIR', 'RED']).rename('NDVI')
        
        if ndvi_image is None:
            logging.error("Failed to generate NDVI image for Landsat.")
            return None, None
        
        logging.info("Successfully created Landsat NDVI visualization")
        return ndvi_image, get_ndvi_vis_params()
    except Exception as e:
        logging.error(f"Error in add_landsat_ndvi: {e}", exc_info=True)
        # Log the dates that caused the error
        logging.error(f"Error occurred with dates: start={start_date}, end={end_date}")
        return None, None

def apply_scale_factors(image):
    """Applies scaling factors to Landsat 8/9 surface reflectance and thermal bands."""
    # Apply scale factor and offset to optical bands (SR_B*)
    opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    # Apply scale factor and offset to thermal bands (ST_B*)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    # Add the scaled bands back to the image, overwriting the original bands
    return image.addBands(opticalBands, None, True).addBands(thermalBands, None, True)

def get_ndvi_vis_params():
    """Return standard NDVI visualization parameters for consistency"""
    return {
        'min': -0.2,
        'max': 0.8,
        'palette': [
            'FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
            '74A901', '66A000', '529400', '3E8601', '207401', '056201',
            '004C00', '023B01', '012E01', '011D01', '011301'
        ]
    }