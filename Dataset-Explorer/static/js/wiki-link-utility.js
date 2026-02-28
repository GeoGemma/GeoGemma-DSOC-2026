/**
 * Utility to convert remote sensing and GEE keywords to Wikipedia links
 * Only capitalized terms will be linked
 */
const WikiLinkUtility = {
  /**
   * Common remote sensing and Earth observation keywords that likely have Wikipedia pages
   * This list can be expanded over time
   */
  keywords: [
    // Satellite missions and programs
    'Landsat', 'MODIS', 'Sentinel-2', 'Sentinel-1','AVHRR', 'VIIRS', 'GOES', 'SPOT', 
    'WorldView', 'QuickBird', 'Ikonos', 'RapidEye', 'Pleiades', 'Planet',
    'SRTM', 'ASTER', 'ALOS', 'PALSAR', 'TerraSAR-X', 'Radarsat', 'MetOp',
    'TRMM', 'GPM', 'ICESat', 'GRACE', 'GEDI', 'CYGNSS', 'Envisat',
    'Jason', 'Seasat', 'SARAL', 'TOPEX', 'Aqua', 'Terra', 'Suomi NPP',
    'NOAA-20', 'JPSS', 'Himawari', 'GeoEye', 'CartoSat', 'KOMPSAT',
    'IRS', 'CBERS', 'Gaofen', 'Ziyuan', 'HyspIRI', 'EnMAP', 'PRISMA',
    
    // Organizations and agencies
    'NASA', 'NOAA', 'USGS', 'ESA', 'JAXA', 'ISRO', 'EUMETSAT', 
    'USDA', 'NASS', 'CNES', 'DLR', 'CSA', 'ASI', 'INPE', 'CONAE',
    'CSIRO', 'KARI', 'CNSA', 'Roscosmos', 'GEO', 'CEOS', 'GEOSS',
    
    // Remote sensing concepts
    'Remote Sensing', 'Earth Observation', 'GIS', 'Photogrammetry',
    'NDVI', 'EVI', 'SAVI', 'NDWI', 'NDBI', 'SAR', 'InSAR', 'LiDAR',
    'Multispectral', 'Hyperspectral', 'Thermal Infrared', 'Radar',
    'False Color', 'True Color', 'Pan-sharpening', 'Digital Elevation Model',
    'Supervised Classification', 'Unsupervised Classification',
    'Object-based Image Analysis', 'Change Detection', 'Land Cover',
    'Land Use', 'Atmospheric Correction', 'Radiometric Correction',
    'Geometric Correction', 'Orthorectification', 'Time Series Analysis',
    
    // Satellite bands and sensors
    'Near-infrared', 'Shortwave Infrared', 'Thermal Infrared', 'Microwave',
    'C-band', 'L-band', 'X-band', 'P-band', 'SWIR', 'NIR', 'VNIR', 'TIR', 
    'OLI', 'TIRS', 'MSI', 'SEVIRI', 'OLCI', 'SLSTR', 'VIIRS', 'AVHRR',
    'ETM+', 'TM', 'MSS', 'ASTER GDEM', 'Panchromatic',
    
    // Earth science phenomena and topics
    'Climate Change', 'Deforestation', 'Urbanization', 'Drought',
    'Flood', 'Wildfire', 'Land Degradation', 'Biodiversity',
    'Carbon Cycle', 'Water Cycle', 'Albedo', 'Evapotranspiration',
    'Sea Level Rise', 'Ocean Acidification', 'Coral Bleaching',
    'Desertification', 'El Niño', 'La Niña', 'Monsoon', 'Urban Heat Island',
    
    // GEE specific
    'Google Earth Engine', 'Earth Engine', 'GEE', 'Cloud Computing',
    'BigQuery', 'Feature Collection', 'Image Collection'
  ],
  
  /**
   * Convert known keywords in text to Wikipedia links
   * ONLY if they are capitalized
   * 
   * @param {string} text - The text containing potential keywords
   * @returns {string} - Text with keywords converted to links
   */
  addWikipediaLinks: function(text) {
    if (!text) return '';
    
    // Sort keywords by length (descending) to match longer phrases first
    const sortedKeywords = this.keywords.sort((a, b) => b.length - a.length);
    
    // Create a regex pattern for each keyword that ensures it's a whole word
    // This uses word boundaries \b to avoid matching parts of words
    let processedText = text;
    
    for (const keyword of sortedKeywords) {
      // Create regex with word boundaries and case-sensitive matching
      // Use captured group to preserve original capitalization
      const regex = new RegExp(`\\b(${keyword})\\b`, 'g');
      
      // Replace matches with Wikipedia links, but ONLY if they match the case (capitalized)
      processedText = processedText.replace(regex, (match, p1) => {
        // Only create link if the match has the same case as our keyword
        // This ensures we only link capitalized terms
        if (match === keyword) {
          const encodedKeyword = encodeURIComponent(match);
          return `<a href="https://en.wikipedia.org/wiki/${encodedKeyword}" target="_blank" class="wiki-link" title="Learn more about ${match} on Wikipedia">${match}</a>`;
        }
        // Return the original text if not a capitalized match
        return match;
      });
    }
    
    return processedText;
  }
};