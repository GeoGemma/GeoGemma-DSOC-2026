/**
 * Utility functions for the GEE Dataset Explorer
 */
const Utils = {
  /**
   * Show loading indicator
   */
  showLoading: function() {
    document.getElementById('loadingIndicator').style.display = 'block';
  },
  
  /**
   * Hide loading indicator
   */
  hideLoading: function() {
    document.getElementById('loadingIndicator').style.display = 'none';
  },
  
  /**
   * Validate and potentially fix a bounding box
   * @param {Array} bbox - The bounding box to validate [west, south, east, north]
   * @returns {Array|null} - The fixed bounding box or null if invalid
   */
  validateAndFixBbox: function(bbox) {
    // If bbox exists and has correct length
    if (bbox && Array.isArray(bbox) && bbox.length === 4) {
      console.log("Original bbox:", bbox);
      
      // Check for valid coordinate values
      let validCoords = bbox.every(coord => typeof coord === 'number' && !isNaN(coord));
      if (!validCoords) {
        console.error("Invalid bbox coordinates (NaN or non-numeric):", bbox);
        return null;
      }
      
      // Make a copy of the bbox
      let fixedBbox = [...bbox];
      
      // Check if the longitude values (0 and 2) are within reasonable range (-180 to 180)
      if (fixedBbox[0] < -180 || fixedBbox[0] > 180 || fixedBbox[2] < -180 || fixedBbox[2] > 180) {
        console.warn("Suspicious longitude values in bbox:", fixedBbox);
        
        // If longitudes appear to be swapped with latitudes, fix them
        if ((fixedBbox[0] >= -90 && fixedBbox[0] <= 90) && 
            (fixedBbox[2] >= -90 && fixedBbox[2] <= 90) &&
            (fixedBbox[1] >= -180 && fixedBbox[1] <= 180) && 
            (fixedBbox[3] >= -180 && fixedBbox[3] <= 180)) {
            
            console.log("Detected swapped lat/lon, fixing bbox");
            
            // Swap coordinates to fix [lon, lat, lon, lat] to [lat, lon, lat, lon] format
            const temp = fixedBbox[0];
            fixedBbox[0] = fixedBbox[1];
            fixedBbox[1] = temp;
            
            const temp2 = fixedBbox[2];
            fixedBbox[2] = fixedBbox[3];
            fixedBbox[3] = temp2;
        }
      }
      
      // Check if min/max are reversed (min > max)
      if (fixedBbox[0] > fixedBbox[2]) {
        console.warn("Longitude values appear reversed (min > max), fixing");
        [fixedBbox[0], fixedBbox[2]] = [fixedBbox[2], fixedBbox[0]];
      }
      
      if (fixedBbox[1] > fixedBbox[3]) {
        console.warn("Latitude values appear reversed (min > max), fixing");
        [fixedBbox[1], fixedBbox[3]] = [fixedBbox[3], fixedBbox[1]];
      }
      
      // Check for extreme values that suggest a potential issue
      if (fixedBbox[1] < -85 && fixedBbox[3] < -80) {
        console.warn("Detected bbox in Antarctica, this might indicate a problem. Original:", bbox, "Fixed:", fixedBbox);
        return null;
      }
      
      console.log("Fixed bbox:", fixedBbox);
      return fixedBbox;
    }
    
    return null;
  },
  
  /**
   * Log dataset response data for debugging
   * @param {Object} data - The dataset response data
   */
  inspectDatasetResponse: function(data) {
    console.log("DATASET RESPONSE INSPECTION:");
    console.log("- Dataset has js_map_center:", !!data.js_map_center);
    if (data.js_map_center) {
      console.log("  - js_map_center values:", data.js_map_center);
    }
    console.log("- Dataset has lookat:", !!data.lookat);
    if (data.lookat) {
      console.log("  - lookat values:", data.lookat);
    }
    console.log("- Dataset has bbox:", !!data.bbox);
    if (data.bbox) {
      console.log("  - bbox values:", data.bbox);
    }
  },
  
/**
 * Create a visual representation of the color palette with enhanced description
 * @param {Array} palette - Array of color values
 * @param {number|string} min - Minimum value for the palette
 * @param {number|string} max - Maximum value for the palette
 * @param {Array} classDescriptions - Optional descriptions for palette classes
 * @param {String} datasetId - Optional dataset ID to determine domain-specific info
 * @returns {string} - HTML for the palette display
 */
createPaletteDisplay : function(palette, min, max, classDescriptions, datasetId = '') {
  // Ensure we have valid input
  if (!palette || !Array.isArray(palette) || palette.length === 0) {
    console.log("No palette information available.");
    return "<p>No palette information available.</p>";
  }
  
  console.log("Creating palette display with:", { palette, min, max, classDescriptions });
  
  // Ensure all color values have # prefix if they're hex colors
  const processedPalette = palette.map(color => {
    // Skip non-string values
    if (typeof color !== 'string') return color;
    
    // Add # prefix if it's a valid hex code without #
    if (color.match(/^[0-9A-Fa-f]{6}$/)) {
      return '#' + color;
    }
    // Already has # or is a named color
    return color;
  });
  
  // Determine the units and description based on the dataset ID or content
  let valueUnit = '';
  let valueDescription = '';
  
  // Try to determine units and descriptions based on dataset ID or other hints
  if (datasetId) {
    if (datasetId.includes('NDVI') || datasetId.includes('ndvi')) {
      valueUnit = 'Index';
      valueDescription = 'NDVI (Normalized Difference Vegetation Index) ranges from -1 to 1, where higher values indicate dense vegetation.';
    } else if (datasetId.includes('EVI') || datasetId.includes('evi')) {
      valueUnit = 'Index';
      valueDescription = 'EVI (Enhanced Vegetation Index) typically ranges from -1 to 1, with higher values indicating healthier vegetation.';
    } else if (datasetId.includes('LST') || datasetId.includes('temperature')) {
      valueUnit = '°C or K';
      valueDescription = 'Land Surface Temperature values, typically in degrees Celsius or Kelvin.';
    } else if (datasetId.includes('precipitation') || datasetId.includes('rainfall')) {
      valueUnit = 'mm';
      valueDescription = 'Precipitation values, typically measured in millimeters.';
    } else if (datasetId.includes('elevation') || datasetId.includes('DEM') || datasetId.includes('srtm')) {
      valueUnit = 'm';
      valueDescription = 'Elevation values, measured in meters above sea level.';
    } else if (datasetId.includes('landcover') || datasetId.includes('WorldCover')) {
      valueUnit = 'Class';
      valueDescription = 'Land cover classification values representing different surface types.';
    } else if (datasetId.includes('sentinel-1') || datasetId.includes('SAR')) {
      valueUnit = 'dB';
      valueDescription = 'Radar backscatter intensity values, measured in decibels (dB).';
    } else {
      // Default description for other datasets
      valueUnit = '';
      valueDescription = 'The color scale represents the range of values in the selected band.';
    }
  }
  
  var html = '<div class="palette-container">' +
            '<div class="palette-title">Color Palette</div>';
  
  // Add the determined value description if available
  if (valueDescription) {
    html += `<div class="palette-description">${valueDescription}</div>`;
  }
  
  // If we have class descriptions, display them as a legend
  if (classDescriptions && Array.isArray(classDescriptions) && classDescriptions.length > 0) {
    html += '<table style="width:100%; margin-bottom:10px; font-size:12px;">';
    classDescriptions.forEach(function(cls) {
      if (cls && cls.color && cls.description) {
        var color = cls.color.startsWith('#') ? cls.color : '#' + cls.color;
        html += '<tr>' +
               '<td style="width:20px; background-color:' + color + ';">&nbsp;</td>' +
               '<td style="padding-left:5px;">' + cls.description + ' (Value: ' + (cls.value || 'N/A') + ')</td>' +
               '</tr>';
      }
    });
    html += '</table>';
  } else {
    // Otherwise display the simple color ramp
    html += '<div class="palette-display" style="display:flex; height:20px; width:100%; margin:5px 0;">';
    
    // Create color blocks for each color in the palette
    for (var i = 0; i < processedPalette.length; i++) {
      html += '<div class="palette-color" style="flex:1; background-color:' + processedPalette[i] + ';"></div>';
    }
    
    html += '</div>' +
            '<div class="palette-labels" style="display:flex; justify-content:space-between; margin-top:4px; font-size:12px;">' +
            '<span>' + min + (valueUnit ? ' ' + valueUnit : '') + '</span>' +
            '<span>' + max + (valueUnit ? ' ' + valueUnit : '') + '</span>' +
            '</div>';
  }
  
  html += '</div>';
  console.log("Generated palette HTML");
  return html;
}
};