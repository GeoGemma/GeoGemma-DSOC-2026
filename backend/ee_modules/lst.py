import ee
import logging
import datetime
import re
from typing import Optional, Tuple, Dict, Union, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_year_input(year_input):
    """
    Parse various year formats and return a standardized year integer or "latest".
    Handles YYYY format, date strings, and "latest" keyword.
    """
    if year_input is None:
        return None
        
    # Handle "latest" keyword
    if isinstance(year_input, str) and "latest" in year_input.lower():
        return "latest"
        
    # Handle year as integer
    if isinstance(year_input, int):
        return year_input
        
    # Handle year as string in YYYY format
    if isinstance(year_input, str) and re.match(r'^\d{4}$', year_input):
        return int(year_input)
        
    # Handle YYYY-MM-DD format
    if isinstance(year_input, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', year_input):
        return int(year_input.split('-')[0])
    
    # Handle month-year combinations
    month_year_patterns = [
        r'(\w+)\s+(\d{4})',      # March 2022
        r'(\d{1,2})[/-](\d{4})',  # 03/2022 or 03-2022
        r'(\d{4})[/-](\d{1,2})'   # 2022/03 or 2022-03
    ]
    
    for pattern in month_year_patterns:
        if isinstance(year_input, str):
            match = re.match(pattern, year_input)
            if match:
                # Extract year from pattern
                if match.group(1).isdigit() and int(match.group(1)) > 12:
                    # Format is YYYY-MM
                    return int(match.group(1))
                else:
                    # Other formats where year is second group
                    return int(match.group(2))
    
    # Look for year in the string
    if isinstance(year_input, str):
        # Find any 4-digit number that looks like a year (1980-2030)
        year_matches = re.findall(r'\b(19[8-9][0-9]|20[0-3][0-9])\b', year_input)
        if year_matches:
            # Use the first valid year found
            return int(year_matches[0])
    
    # If none of the patterns match, try to use current year
    logging.warning(f"Could not parse year from '{year_input}', using current year")
    return datetime.datetime.now().year

def extract_date_info_from_inputs(year_input, start_date=None, end_date=None):
    """
    Extract year, month, and determine if this is a specific date range request.
    Used to ensure proper date handling for LST requests.
    
    Returns:
        tuple: (year, month, is_date_range_request)
    """
    year = None
    month = None
    is_date_range_request = False
    
    # Check if we have explicit start/end dates provided
    if start_date and end_date:
        # This is a date range request
        is_date_range_request = True
        
        # Extract year from start date (assuming YYYY-MM-DD format)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', start_date):
            year = int(start_date.split('-')[0])
            month = int(start_date.split('-')[1])
        
        logging.info(f"Explicit date range provided: {start_date} to {end_date}")
        logging.info(f"Extracted year: {year}, month: {month}")
        return year, month, is_date_range_request
    
    # If no explicit dates, try to extract from year_input
    if isinstance(year_input, str):
        # Check for month information in the string
        month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        # Check for month name
        for month_name, month_num in month_names.items():
            if month_name in year_input.lower():
                month = month_num
                break
        
        # Check for MM/YYYY or YYYY/MM or YYYY-MM patterns
        if not month:
            # Try MM/YYYY or MM-YYYY pattern
            mm_yyyy_match = re.search(r'(\d{1,2})[/-](\d{4})', year_input)
            if mm_yyyy_match and int(mm_yyyy_match.group(1)) <= 12:
                month = int(mm_yyyy_match.group(1))
                year = int(mm_yyyy_match.group(2))
            
            # Try YYYY/MM or YYYY-MM pattern
            yyyy_mm_match = re.search(r'(\d{4})[/-](\d{1,2})', year_input)
            if yyyy_mm_match and int(yyyy_mm_match.group(2)) <= 12:
                year = int(yyyy_mm_match.group(1))
                month = int(yyyy_mm_match.group(2))
    
    # If still no year, parse year_input normally
    if year is None:
        year = parse_year_input(year_input)
    
    return year, month, is_date_range_request

def extract_month_from_input(input_str):
    """
    Extract month from input string (used for seasonal processing).
    Returns month number (1-12) or None.
    """
    if not isinstance(input_str, str):
        return None
        
    month_names = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
        # Add seasons as approximate month ranges
        'winter': 1,  # Northern hemisphere winter
        'spring': 4,  # Northern hemisphere spring
        'summer': 7,  # Northern hemisphere summer
        'fall': 10, 'autumn': 10  # Northern hemisphere fall
    }
    
    # Check for month names
    for month_name, month_num in month_names.items():
        if month_name in input_str.lower():
            return month_num
            
    # Check for MM/YYYY or YYYY/MM patterns
    month_patterns = [
        r'(\d{1,2})[/-](\d{4})',  # MM/YYYY
        r'(\d{4})[/-](\d{1,2})'   # YYYY/MM
    ]
    
    for pattern in month_patterns:
        match = re.search(pattern, input_str)
        if match:
            if match.group(1).isdigit() and int(match.group(1)) <= 12:
                # Pattern is MM/YYYY
                return int(match.group(1))
            elif match.group(2).isdigit() and int(match.group(2)) <= 12:
                # Pattern is YYYY/MM
                return int(match.group(2))
    
    return None

def get_season_date_range(year, month):
    """
    Get a date range for a season based on year and month.
    Returns (start_date, end_date) as strings.
    """
    # Define seasons (approximate)
    if month in [12, 1, 2]:  # Winter
        if month == 12:
            return f"{year}-12-01", f"{year+1}-02-28"
        else:
            return f"{year}-12-01", f"{year}-02-28"
    elif month in [3, 4, 5]:  # Spring
        return f"{year}-03-01", f"{year}-05-31"
    elif month in [6, 7, 8]:  # Summer
        return f"{year}-06-01", f"{year}-08-31"
    elif month in [9, 10, 11]:  # Fall/Autumn
        return f"{year}-09-01", f"{year}-11-30"
    else:
        return f"{year}-01-01", f"{year}-12-31"  # Full year fallback

def get_month_date_range(year, month):
    """
    Get a date range for a specific month.
    Returns (start_date, end_date) as strings.
    """
    # Calculate the end date of the month
    if month == 12:
        next_month_year = year + 1
        next_month = 1
    else:
        next_month_year = year
        next_month = month + 1
    
    # Start date is first day of the month
    start_date = f"{year}-{month:02d}-01"
    
    # End date is last day of the month (one day before the first day of next month)
    end_date = f"{next_month_year}-{next_month:02d}-01"
    end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.timedelta(days=1)
    end_date = end_date_obj.strftime("%Y-%m-%d")
    
    return start_date, end_date

def get_latest_lst(geometry):
    """
    Fetches the most recent Landsat LST data available with improved reliability.
    
    Args:
        geometry (ee.Geometry): The region of interest.
        
    Returns:
        tuple: (ee.Image, dict) containing the LST image and visualization parameters,
               or (None, None) if an error occurred.
    """
    try:
        # Get today's date and date 120 days ago for search window (increased from 90)
        today = datetime.date.today()
        search_start = (today - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
        search_end = today.strftime('%Y-%m-%d')
        
        # Function for masking and preprocessing imagery
        def maskL89sr(image):
            qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
            saturationMask = image.select('QA_RADSAT').eq(0)

            def getFactorImg(factorNames):
                factorList = image.toDictionary().select(factorNames).values()
                return ee.Image.constant(factorList)

            scaleImg = getFactorImg(['REFLECTANCE_MULT_BAND_.|TEMPERATURE_MULT_BAND_.*'])
            offsetImg = getFactorImg(['REFLECTANCE_ADD_BAND_.|TEMPERATURE_ADD_BAND_.*'])
            scaled = image.select('SR_B.|ST_B.*').multiply(scaleImg).add(offsetImg)

            return image.addBands(scaled, None, True).updateMask(qaMask).updateMask(saturationMask)

        def maskL457sr(image):
            qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
            saturationMask = image.select('QA_RADSAT').eq(0)

            def getFactorImg(factorNames):
                factorList = image.toDictionary().select(factorNames).values()
                return ee.Image.constant(factorList)

            scaleImg = getFactorImg(['REFLECTANCE_MULT_BAND_.|TEMPERATURE_MULT_BAND_ST_B6'])
            offsetImg = getFactorImg(['REFLECTANCE_ADD_BAND_.|TEMPERATURE_ADD_BAND_ST_B6'])
            scaled = image.select('SR_B.|ST_B6').multiply(scaleImg).add(offsetImg)

            return image.addBands(scaled, None, True).updateMask(qaMask).updateMask(saturationMask)

        def addIndices(image):
            # L8/L9 indices
            ndviL89 = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
            eviL89 = image.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                    'NIR': image.select('SR_B5'),
                    'RED': image.select('SR_B4'),
                    'BLUE': image.select('SR_B2')
                }).rename('EVI')
            ndbiL89 = image.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')

            # L7 indices
            ndviL7 = image.normalizedDifference(['SR_B4', 'SR_B3']).rename('NDVI')
            eviL7 = image.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                    'NIR': image.select('SR_B4'),
                    'RED': image.select('SR_B3'),
                    'BLUE': image.select('SR_B1')
                }).rename('EVI')
            ndbiL7 = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDBI')

            # Choose the correct indices based on satellite
            satelliteId = ee.String(image.get('SPACECRAFT_ID'))
            ndvi = ee.Image(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                ndviL7,
                ndviL89
            ))

            evi = ee.Image(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                eviL7,
                eviL89
            ))

            ndbi = ee.Image(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                ndbiL7,
                ndbiL89
            ))

            return image.addBands(ndvi).addBands(evi).addBands(ndbi)

        def getEmissivity(image):
            fvc = image.expression(
                '((NDVI - NDVI_soil) / (NDVI_veg - NDVI_soil))**2', {
                    'NDVI': image.select('NDVI'),
                    'NDVI_soil': 0.2,
                    'NDVI_veg': 0.86
                })
            fvc = fvc.max(0).min(1)

            emissivity = image.expression(
                '(e_v * FVC) + (e_s * (1 - FVC)) + (1 - e_s) * 0.05 * FVC', {
                    'FVC': fvc,
                    'e_v': 0.99,
                    'e_s': 0.95
                }).rename('emissivity')

            return image.addBands(emissivity)

        def addLST(image):
            satelliteId = ee.String(image.get('SPACECRAFT_ID'))
            thermalBand = ee.String(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                'ST_B6',
                'ST_B10'
            ))

            k1 = ee.Number(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                666.09,
                ee.Algorithms.If(
                    satelliteId.equals('LANDSAT_8'),
                    774.8853,
                    799.0289
                )
            ))

            k2 = ee.Number(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                1282.71,
                ee.Algorithms.If(
                    satelliteId.equals('LANDSAT_8'),
                    1321.0789,
                    1324.7999
                )
            ))

            brightnessTemp = image.select(thermalBand)

            lst = image.expression(
                '(TB / (1 + (0.00115 * TB / 1.4388) * log(e))) - 273.15', {
                    'TB': brightnessTemp,
                    'e': image.select('emissivity')
                }).rename('LST_Celsius')

            return image.addBands(lst)

        # Create a function for processing images consistently
        def process_landsat_image(image):
            # Determine which preprocessing function to use based on the satellite
            satelliteId = ee.String(image.get('SPACECRAFT_ID')).getInfo()
            
            if satelliteId in ['LANDSAT_8', 'LANDSAT_9']:
                processed = maskL89sr(image)
            else:  # LANDSAT_7 or others
                processed = maskL457sr(image)
                
            processed = addIndices(processed)
            processed = getEmissivity(processed)
            processed = addLST(processed)
            return processed

        # Try Landsat 9 first (newest)
        l9_collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
            .filterBounds(geometry) \
            .filterDate(search_start, search_end) \
            .filter(ee.Filter.lt('CLOUD_COVER', 35))  # Increased cloud threshold
            
        l9_size = l9_collection.size().getInfo()
        logging.info(f"Found {l9_size} Landsat 9 images in the last 120 days")
        
        if l9_size > 0:
            # Process the most recent L9 image
            l9_collection = l9_collection.sort('system:time_start', False)
            most_recent_l9 = l9_collection.first()
            
            # Get image date for logging
            image_date = ee.Date(most_recent_l9.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            logging.info(f"Using most recent Landsat 9 image from {image_date}")
            
            # Process the image
            processed_image = process_landsat_image(most_recent_l9)
            
            # Select LST band
            lstImage = processed_image.select('LST_Celsius')
            
        else:
            # Try Landsat 8 if no L9 data
            l8_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                .filterBounds(geometry) \
                .filterDate(search_start, search_end) \
                .filter(ee.Filter.lt('CLOUD_COVER', 35))  # Increased cloud threshold
                
            l8_size = l8_collection.size().getInfo()
            logging.info(f"Found {l8_size} Landsat 8 images in the last 120 days")
            
            if l8_size > 0:
                # Process the most recent L8 image
                l8_collection = l8_collection.sort('system:time_start', False)
                most_recent_l8 = l8_collection.first()
                
                # Get image date for logging
                image_date = ee.Date(most_recent_l8.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                logging.info(f"Using most recent Landsat 8 image from {image_date}")
                
                # Process the image
                processed_image = process_landsat_image(most_recent_l8)
                
                # Select LST band
                lstImage = processed_image.select('LST_Celsius')
                
            else:
                # Try Landsat 7 as a last resort (expand search to 180 days)
                extended_search_start = (today - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
                l7_collection = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2') \
                    .filterBounds(geometry) \
                    .filterDate(extended_search_start, search_end) \
                    .filter(ee.Filter.lt('CLOUD_COVER', 40))  # Further increased cloud threshold
                    
                l7_size = l7_collection.size().getInfo()
                logging.info(f"Found {l7_size} Landsat 7 images in the last 180 days")
                
                if l7_size > 0:
                    # Process the most recent L7 image
                    l7_collection = l7_collection.sort('system:time_start', False)
                    most_recent_l7 = l7_collection.first()
                    
                    # Get image date for logging
                    image_date = ee.Date(most_recent_l7.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    logging.info(f"Using most recent Landsat 7 image from {image_date}")
                    
                    # Process the image
                    processed_image = process_landsat_image(most_recent_l7)
                    
                    # Select LST band
                    lstImage = processed_image.select('LST_Celsius')
                    
                else:
                    logging.warning("No recent Landsat imagery found")
                    return None, None
                    
        # Calculate min and max values for better visualization
        minMax = lstImage.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=geometry.buffer(50000),
            scale=100,
            maxPixels=1e9
        )

        # Extract min and max LST values
        minTemp = ee.Number(minMax.get('LST_Celsius_min'))
        maxTemp = ee.Number(minMax.get('LST_Celsius_max'))

        # Define visualization parameters using the calculated min/max
        lstVis = {
            'min': minTemp,
            'max': maxTemp,
            'palette': [
                '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
                '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
                '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
                'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
                'ff0000', 'de0101', 'c21301', 'a71001', '911003'
            ]
        }

        return lstImage, lstVis

    except Exception as e:
        logging.error(f"Error in get_latest_lst: {e}", exc_info=True)
        return None, None

def add_landsat_lst(geometry, year=None, start_date=None, end_date=None):
    """
    Calculates Land Surface Temperature (LST) from Landsat data.
    Enhanced to handle explicit date ranges and month specifications.
    
    Args:
        geometry (ee.Geometry): The region of interest.
        year (int, str): The year/date reference for which to calculate LST.
        start_date (str, optional): Explicit start date if provided by the caller.
        end_date (str, optional): Explicit end date if provided by the caller.
        
    Returns:
        tuple: (ee.Image, dict) containing the LST image and visualization parameters,
               or (None, None) if an error occurred.
    """
    try:
        # Extract date information from inputs - this is the key enhancement
        original_year_input = year
        parsed_year, month, is_date_range_request = extract_date_info_from_inputs(year, start_date, end_date)
        
        # Handle "latest" case
        if parsed_year == "latest":
            logging.info("Fetching latest LST imagery")
            return get_latest_lst(geometry)
            
        # Default to current year if not specified
        if parsed_year is None:
            parsed_year = datetime.datetime.now().year
            logging.info(f"No year specified for LST, using current year: {parsed_year}")
            
        # Validate year range (Landsat data available from 1982 onwards)
        current_year = datetime.datetime.now().year
        if parsed_year < 1982 or parsed_year > current_year:
            logging.error(f"Invalid year for LST: {parsed_year}. Must be between 1982 and {current_year}")
            return None, None
        
        # Log what we're creating based on the inputs
        if month:
            logging.info(f"Creating LST visualization for month {month} in year {parsed_year}")
        else:
            logging.info(f"Creating LST visualization for year: {parsed_year}")
        
        # Common preprocessing functions
        def maskL89sr(image):
            qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
            saturationMask = image.select('QA_RADSAT').eq(0)

            def getFactorImg(factorNames):
                factorList = image.toDictionary().select(factorNames).values()
                return ee.Image.constant(factorList)

            scaleImg = getFactorImg(['REFLECTANCE_MULT_BAND_.|TEMPERATURE_MULT_BAND_.*'])
            offsetImg = getFactorImg(['REFLECTANCE_ADD_BAND_.|TEMPERATURE_ADD_BAND_.*'])
            scaled = image.select('SR_B.|ST_B.*').multiply(scaleImg).add(offsetImg)

            return image.addBands(scaled, None, True).updateMask(qaMask).updateMask(saturationMask)

        def maskL457sr(image):
            qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
            saturationMask = image.select('QA_RADSAT').eq(0)

            def getFactorImg(factorNames):
                factorList = image.toDictionary().select(factorNames).values()
                return ee.Image.constant(factorList)

            scaleImg = getFactorImg(['REFLECTANCE_MULT_BAND_.|TEMPERATURE_MULT_BAND_ST_B6'])
            offsetImg = getFactorImg(['REFLECTANCE_ADD_BAND_.|TEMPERATURE_ADD_BAND_ST_B6'])
            scaled = image.select('SR_B.|ST_B6').multiply(scaleImg).add(offsetImg)

            return image.addBands(scaled, None, True).updateMask(qaMask).updateMask(saturationMask)

        def addIndices(image):
            # L8/L9 indices
            ndviL89 = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
            eviL89 = image.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                    'NIR': image.select('SR_B5'),
                    'RED': image.select('SR_B4'),
                    'BLUE': image.select('SR_B2')
                }).rename('EVI')
            ndbiL89 = image.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')

            # L7 indices
            ndviL7 = image.normalizedDifference(['SR_B4', 'SR_B3']).rename('NDVI')
            eviL7 = image.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                    'NIR': image.select('SR_B4'),
                    'RED': image.select('SR_B3'),
                    'BLUE': image.select('SR_B1')
                }).rename('EVI')
            ndbiL7 = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDBI')

            # Choose the correct indices based on satellite
            satelliteId = ee.String(image.get('SPACECRAFT_ID'))
            ndvi = ee.Image(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                ndviL7,
                ndviL89
            ))

            evi = ee.Image(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                eviL7,
                eviL89
            ))

            ndbi = ee.Image(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                ndbiL7,
                ndbiL89
            ))

            return image.addBands(ndvi).addBands(evi).addBands(ndbi)

        def getEmissivity(image):
            fvc = image.expression(
                '((NDVI - NDVI_soil) / (NDVI_veg - NDVI_soil))**2', {
                    'NDVI': image.select('NDVI'),
                    'NDVI_soil': 0.2,
                    'NDVI_veg': 0.86
                })
            fvc = fvc.max(0).min(1)

            emissivity = image.expression(
                '(e_v * FVC) + (e_s * (1 - FVC)) + (1 - e_s) * 0.05 * FVC', {
                    'FVC': fvc,
                    'e_v': 0.99,
                    'e_s': 0.95
                }).rename('emissivity')

            return image.addBands(emissivity)

        def addLST(image):
            satelliteId = ee.String(image.get('SPACECRAFT_ID'))
            thermalBand = ee.String(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                'ST_B6',
                'ST_B10'
            ))

            k1 = ee.Number(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                666.09,
                ee.Algorithms.If(
                    satelliteId.equals('LANDSAT_8'),
                    774.8853,
                    799.0289
                )
            ))

            k2 = ee.Number(ee.Algorithms.If(
                satelliteId.equals('LANDSAT_7'),
                1282.71,
                ee.Algorithms.If(
                    satelliteId.equals('LANDSAT_8'),
                    1321.0789,
                    1324.7999
                )
            ))

            brightnessTemp = image.select(thermalBand)

            lst = image.expression(
                '(TB / (1 + (0.00115 * TB / 1.4388) * log(e))) - 273.15', {
                    'TB': brightnessTemp,
                    'e': image.select('emissivity')
                }).rename('LST_Celsius')

            return image.addBands(lst)

        # Set date range based on inputs
        if is_date_range_request:
            # Use the explicit start/end dates provided
            startYearDate = ee.Date(start_date)
            endYearDate = ee.Date(end_date)
            logging.info(f"Using explicit date range: {start_date} to {end_date}")
        elif month:
            # Use specific month if detected
            start_date, end_date = get_month_date_range(parsed_year, month)
            startYearDate = ee.Date(start_date)
            endYearDate = ee.Date(end_date)
            logging.info(f"Using month-specific date range: {start_date} to {end_date}")
        else:
            # Default: use Jan-May window
            startYearDate = ee.Date.fromYMD(parsed_year, 1, 1)
            endYearDate = ee.Date.fromYMD(parsed_year, 5, 31)
            logging.info(f"Using default date range (Jan-May): {startYearDate.format('YYYY-MM-dd').getInfo()} to {endYearDate.format('YYYY-MM-dd').getInfo()}")

        # Initialize variables to track available images
        l9_images = None
        l8_images = None
        l7_images = None
        l9_size = 0
        l8_size = 0
        l7_size = 0
        
        # Check for Landsat 9 (launched September 2021)
        if parsed_year >= 2021:
            l9_collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
                .filterBounds(geometry) \
                .filterDate(startYearDate, endYearDate) \
                .filter(ee.Filter.lt('CLOUD_COVER', 35))  # Increased cloud threshold
            
            l9_size = l9_collection.size().getInfo()
            logging.info(f"Found {l9_size} Landsat 9 images for {parsed_year}")
            
            if l9_size > 0:
                l9_images = l9_collection.map(maskL89sr).map(addIndices).map(getEmissivity).map(addLST)

        # Check for Landsat 8 (launched February 2013)
        if parsed_year >= 2013:
            l8_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                .filterBounds(geometry) \
                .filterDate(startYearDate, endYearDate) \
                .filter(ee.Filter.lt('CLOUD_COVER', 35))  # Increased cloud threshold
            
            l8_size = l8_collection.size().getInfo()
            logging.info(f"Found {l8_size} Landsat 8 images for {parsed_year}")
            
            if l8_size > 0:
                l8_images = l8_collection.map(maskL89sr).map(addIndices).map(getEmissivity).map(addLST)

        # Check for Landsat 7 (launched April 1999)
        if parsed_year >= 1999:
            l7_collection = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2') \
                .filterBounds(geometry) \
                .filterDate(startYearDate, endYearDate) \
                .filter(ee.Filter.lt('CLOUD_COVER', 40))  # Increased cloud threshold for L7
            
            l7_size = l7_collection.size().getInfo()
            logging.info(f"Found {l7_size} Landsat 7 images for {parsed_year}")
            
            if l7_size > 0:
                l7_images = l7_collection.map(maskL457sr).map(addIndices).map(getEmissivity).map(addLST)

        # If no images were found in the primary date range, try expanding the range
        if l9_size == 0 and l8_size == 0 and l7_size == 0:
            logging.warning(f"No Landsat imagery found for {parsed_year} in primary date range. Expanding search...")
            
            # If month was specified, try the whole year
            if month:
                expanded_start = ee.Date.fromYMD(parsed_year, 1, 1)
                expanded_end = ee.Date.fromYMD(parsed_year, 12, 31)
                logging.info(f"Expanding from month {month} to full year: {expanded_start.format('YYYY-MM-dd').getInfo()} to {expanded_end.format('YYYY-MM-dd').getInfo()}")
            else:
                # Otherwise expand to full year if we were using default Jan-May
                expanded_start = ee.Date.fromYMD(parsed_year, 1, 1)
                expanded_end = ee.Date.fromYMD(parsed_year, 12, 31)
                logging.info(f"Expanding to full year range: {expanded_start.format('YYYY-MM-dd').getInfo()} to {expanded_end.format('YYYY-MM-dd').getInfo()}")
            
            # Try the expanded range with all satellites
            if parsed_year >= 2021:
                l9_collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
                    .filterBounds(geometry) \
                    .filterDate(expanded_start, expanded_end) \
                    .filter(ee.Filter.lt('CLOUD_COVER', 40))  # Further increased cloud threshold
                
                l9_size = l9_collection.size().getInfo()
                logging.info(f"Found {l9_size} Landsat 9 images in expanded range for {parsed_year}")
                
                if l9_size > 0:
                    l9_images = l9_collection.map(maskL89sr).map(addIndices).map(getEmissivity).map(addLST)
            
            if parsed_year >= 2013 and l9_size == 0:
                l8_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                    .filterBounds(geometry) \
                    .filterDate(expanded_start, expanded_end) \
                    .filter(ee.Filter.lt('CLOUD_COVER', 40))
                
                l8_size = l8_collection.size().getInfo()
                logging.info(f"Found {l8_size} Landsat 8 images in expanded range for {parsed_year}")
                
                if l8_size > 0:
                    l8_images = l8_collection.map(maskL89sr).map(addIndices).map(getEmissivity).map(addLST)
            
            if parsed_year >= 1999 and l9_size == 0 and l8_size == 0:
                l7_collection = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2') \
                    .filterBounds(geometry) \
                    .filterDate(expanded_start, expanded_end) \
                    .filter(ee.Filter.lt('CLOUD_COVER', 45))
                
                l7_size = l7_collection.size().getInfo()
                logging.info(f"Found {l7_size} Landsat 7 images in expanded range for {parsed_year}")
                
                if l7_size > 0:
                    l7_images = l7_collection.map(maskL457sr).map(addIndices).map(getEmissivity).map(addLST)
            
            # If still no images and month was specified, try adjacent years
            if l9_size == 0 and l8_size == 0 and l7_size == 0 and month is not None:
                logging.warning(f"No images found for {parsed_year} even with expanded range. Checking adjacent years for same month...")
                
                # Try one year before and one year after
                prev_year = parsed_year - 1
                next_year = parsed_year + 1
                
                if prev_year >= 1999:  # Oldest Landsat 7 data
                    # Format dates for the same month in previous year
                    prev_start, prev_end = get_month_date_range(prev_year, month)
                    
                    logging.info(f"Checking previous year ({prev_year}) for the same month: {prev_start} to {prev_end}")
                    
                    # Use most recent available satellite for the previous year
                    if prev_year >= 2021:
                        prev_collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
                    elif prev_year >= 2013:
                        prev_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                    else:
                        prev_collection = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
                    
                    prev_collection = prev_collection.filterBounds(geometry) \
                        .filterDate(prev_start, prev_end) \
                        .filter(ee.Filter.lt('CLOUD_COVER', 45))
                    
                    prev_size = prev_collection.size().getInfo()
                    logging.info(f"Found {prev_size} images from previous year ({prev_year})")
                    
                    if prev_size > 0:
                        logging.info(f"Using data from previous year ({prev_year}) for the same month")
                        if prev_year >= 2013:
                            processed_prev = prev_collection.map(maskL89sr).map(addIndices).map(getEmissivity).map(addLST)
                        else:
                            processed_prev = prev_collection.map(maskL457sr).map(addIndices).map(getEmissivity).map(addLST)
                        
                        # Use the previous year's data
                        if prev_year >= 2021:
                            l9_images = processed_prev
                            l9_size = prev_size
                        elif prev_year >= 2013:
                            l8_images = processed_prev
                            l8_size = prev_size
                        else:
                            l7_images = processed_prev
                            l7_size = prev_size
                
                # If still no images, try the next year (only if next_year is <= current year)
                current_year = datetime.datetime.now().year
                if l9_size == 0 and l8_size == 0 and l7_size == 0 and next_year <= current_year:
                    # Format dates for the same month in next year
                    next_start, next_end = get_month_date_range(next_year, month)
                    
                    logging.info(f"Checking next year ({next_year}) for the same month: {next_start} to {next_end}")
                    
                    # Use most recent available satellite for the next year
                    if next_year >= 2021:
                        next_collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
                    elif next_year >= 2013:
                        next_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                    else:
                        next_collection = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
                    
                    next_collection = next_collection.filterBounds(geometry) \
                        .filterDate(next_start, next_end) \
                        .filter(ee.Filter.lt('CLOUD_COVER', 45))
                    
                    next_size = next_collection.size().getInfo()
                    logging.info(f"Found {next_size} images from next year ({next_year})")
                    
                    if next_size > 0:
                        logging.info(f"Using data from next year ({next_year}) for the same month")
                        if next_year >= 2013:
                            processed_next = next_collection.map(maskL89sr).map(addIndices).map(getEmissivity).map(addLST)
                        else:
                            processed_next = next_collection.map(maskL457sr).map(addIndices).map(getEmissivity).map(addLST)
                        
                        # Use the next year's data
                        if next_year >= 2021:
                            l9_images = processed_next
                            l9_size = next_size
                        elif next_year >= 2013:
                            l8_images = processed_next
                            l8_size = next_size
                        else:
                            l7_images = processed_next
                            l7_size = next_size
                            
        # Now select the best available data source (in order of preference L9 > L8 > L7)
        if l9_size > 0:
            lstImage = l9_images.median().select('LST_Celsius')
            logging.info(f"Using Landsat 9 for LST in {parsed_year}")
        elif l8_size > 0:
            lstImage = l8_images.median().select('LST_Celsius')
            logging.info(f"Using Landsat 8 for LST in {parsed_year}")
        elif l7_size > 0:
            lstImage = l7_images.median().select('LST_Celsius')
            logging.info(f"Using Landsat 7 for LST in {parsed_year}")
        else:
            logging.warning(f"No Landsat imagery found for {parsed_year}")
            return None, None

        # Set year property and other metadata
        lstImage = lstImage.set('year', parsed_year)
        
        # If this was a month/season request, add those properties
        if month is not None:
            lstImage = lstImage.set('month', month)
        
        # Set original input as property too
        if original_year_input:
            lstImage = lstImage.set('original_input', original_year_input)

        # Calculate min and max values for better visualization
        minMax = lstImage.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=geometry.buffer(50000),
            scale=300,
            maxPixels=1e9
        )

        # Extract min and max LST values
        minTemp = ee.Number(minMax.get('LST_Celsius_min'))
        maxTemp = ee.Number(minMax.get('LST_Celsius_max'))

        # Define visualization parameters using the calculated min/max
        lstVis = {
            'min': minTemp,
            'max': maxTemp,
            'palette': [
                '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
                '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
                '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
                'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
                'ff0000', 'de0101', 'c21301', 'a71001', '911003'
            ]
        }

        return lstImage, lstVis

    except Exception as e:
        logging.error(f"Error in add_landsat_lst: {e}", exc_info=True)
        return None, None