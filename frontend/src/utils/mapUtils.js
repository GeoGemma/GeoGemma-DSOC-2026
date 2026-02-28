// src/utils/mapUtils.js

export const generateLayerId = (location, processingType) => {
    const timestamp = new Date().getTime();
    return `${location.replace(/\s+/g, '_')}_${processingType}_${timestamp}`;
  };
  
  export const formatLayerLabel = (layer) => {
    let label = `${layer.location} (${layer.processing_type})`;
    if (layer.start_date) {
      label += ` - ${layer.start_date.substring(0, 4)}`;
    }
    return label;
  };
  
  // Simplify and truncate location names for display
  export const formatLocation = (location, maxLength = 25) => {
    if (!location) return '';
    
    // Remove any country suffixes if they exist
    let formatted = location.split(',')[0].trim();
    
    // Truncate if too long
    if (formatted.length > maxLength) {
      formatted = formatted.substring(0, maxLength) + '...';
    }
    
    return formatted;
  };
  
  // Color palette functions for map visualizations
  export const getMapColorPalette = (type) => {
    const palettes = {
      NDVI: [
        'FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
        '74A901', '66A000', '529400', '3E8601', '207401', '056201',
        '004C00', '023B01', '012E01', '011D01', '011301'
      ],
      'SURFACE WATER': [
        '#ffffff', '#d4e7ff', '#a8d1ff', '#7cbaff', '#51a3ff',
        '#258cff', '#0075ff', '#005ebf', '#004080'
      ],
      LST: [
        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
        '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
        '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
        'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
        'ff0000', 'de0101', 'c21301', 'a71001', '911003'
      ],
      LULC: [
        '006400', 'ffbb22', 'ffff4c', 'f096ff', 'fa0000',
        'b4b4b4', 'f0f0f0', '0064c8', '0096a0', '00cf75', 'fae6a0'
      ],
      RGB: ['#ff0000', '#00ff00', '#0000ff'] // Simplified RGB representation
    };
    
    return palettes[type] || palettes.RGB;
  };
  
  // Example prompt generator to help users
  export const getExamplePrompts = () => [
    "Show NDVI in Paris for 2022",
    "RGB imagery of Tokyo from Landsat 8",
    "Surface water in Amsterdam",
    "Land use classification for Berlin",
    "Land surface temperature in Rio de Janeiro for 2021",
    "Show Sentinel-2 imagery of New York from April 2023"
  ];
  
  // Get color for notification based on type
  export const getNotificationColor = (type) => {
    const colors = {
      'success': 'bg-green-600 bg-opacity-90',
      'error': 'bg-red-600 bg-opacity-90',
      'warning': 'bg-yellow-500 bg-opacity-90',
      'info': 'bg-blue-600 bg-opacity-90'
    };
    
    return colors[type] || colors.info;
  };