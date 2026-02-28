/**
 * Map initialization and management
 */
const MapManager = {
  // Map instance
  map: null,
  
  // Base layers
  darkBasemap: null,
  lightBasemap: null,
  satelliteBasemap: null,
  
  // Current settings
  currentBasemap: 'dark',
  overlayLayer: null,
  currentOpacity: 0.7,
  
  /**
   * Initialize the map and base layers
   */
  init: function() {
    // Initialize the Leaflet map
    this.map = L.map('map', {
      preferCanvas: true,  // Use Canvas renderer for better performance
      zoomControl: false,  // Disable default zoom control
      contextmenu: true    // Enable context menu for right-click
    }).setView([20, 0], 2);
    
    // Define different basemap tile layers
    this.darkBasemap = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      maxZoom: 19
    });
    
    this.lightBasemap = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      maxZoom: 19
    });
    
    this.satelliteBasemap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      maxZoom: 19
    });
    
    // Start with dark basemap
    this.darkBasemap.addTo(this.map);
    
    // Set up event listeners
    this.initEventListeners();
    
    // Add combined opacity and zoom controls to the map controls
    this.addControls();
  },
  
  /**
   * Initialize map event listeners
   */
  initEventListeners: function() {
    // Fix for tile loading issues - force reload layers when map is moved
    this.map.on('moveend', () => {
      if (this.overlayLayer) {
        // Slightly adjust opacity to force a redraw
        let currentOp = this.overlayLayer.options.opacity;
        this.overlayLayer.setOpacity(currentOp - 0.01);
        setTimeout(() => {
          this.overlayLayer.setOpacity(currentOp);
        }, 50);
      }
      
      // Log map position in console for debugging
      this.logMapDebugInfo();
    });
    
    // Set up basemap button listeners
    document.getElementById('darkMapBtn').addEventListener('click', () => this.switchBasemap('dark'));
    document.getElementById('lightMapBtn').addEventListener('click', () => this.switchBasemap('light'));
    document.getElementById('satelliteBtn').addEventListener('click', () => this.switchBasemap('satellite'));
    
    // Map keyboard shortcuts for basemap switching
    document.addEventListener('keydown', function(event) {
      if (event.key === '1') MapManager.switchBasemap('dark');
      if (event.key === '2') MapManager.switchBasemap('light');
      if (event.key === '3') MapManager.switchBasemap('satellite');
    });
    
    // Initialize value inspection on right-click
    this.initValueInspection();
  },
  
  /**
   * Initialize right-click listener for value inspection
   */
  initValueInspection: function() {
    // Add a popup for displaying values
    this.infoPopup = L.popup({
      className: 'value-info-popup',
      closeButton: true,
      autoClose: true,
      closeOnEscapeKey: true
    });
    
    // Add context menu (right-click) listener
    this.map.on('contextmenu', (e) => {
      // Only proceed if we have an overlay layer
      if (!this.overlayLayer) {
        return;
      }
      
      // Show loading in the popup while we fetch data
      this.infoPopup
        .setLatLng(e.latlng)
        .setContent('<div class="popup-loading">Loading value information...</div>')
        .openOn(this.map);
      
      // Get the pixel/feature value at this location
      this.getValueAtLocation(e.latlng);
    });
    
    console.log("Value inspection initialized (right-click on map to query values)");
  },
  
/**
 * Get the value at a specific map location
 * @param {L.LatLng} latlng - The latitude and longitude where the user clicked
 */
getValueAtLocation: function(latlng) {
  // Get current dataset ID and type
  const datasetId = DatasetManager.currentDataset;
  const isFeatureCollection = DatasetManager.currentDatasetInfo && 
                             DatasetManager.currentDatasetInfo['gee:type'] === 'table';
  
  if (!datasetId) {
    this.infoPopup.setContent('<div class="popup-error">No dataset loaded</div>');
    return;
  }
  
  // Prepare parameters for the backend API call
  const params = {
    dataset_id: datasetId,
    coordinates: {
      lon: latlng.lng,
      lat: latlng.lat
    },
    get_value: true  // Special flag to indicate we want to query value
  };
  
  // Add current map view center to help with spatial context
  params.js_map_center = {
    lon: this.map.getCenter().lng,
    lat: this.map.getCenter().lat,
    zoom: this.map.getZoom()
  };
  
  // ENHANCEMENT: Include temporal filter if available
  if (DatasetManager.temporalSelection && DatasetManager.temporalSelection.isTemporalDataset) {
    const year = DatasetManager.temporalSelection.year;
    const month = DatasetManager.temporalSelection.month;
    
    // Format month with leading zero if needed
    const monthFormatted = month < 10 ? `0${month}` : `${month}`;
    
    // Create date range for the selected month (1st to last day)
    const startDate = `${year}-${monthFormatted}-01`;
    
    // Get the last day of the month
    const lastDay = new Date(year, month, 0).getDate();
    const endDate = `${year}-${monthFormatted}-${lastDay}`;
    
    params.temporal_filter = {
      start_date: startDate,
      end_date: endDate,
      aggregation: 'median'  // Consistent with visualization
    };
    
    console.log(`Including temporal filter in value query: ${startDate} to ${endDate}`);
  }
  
  // ENHANCEMENT: Include current visualization parameters if available
  if (DatasetManager.selectedBand) {
    params.band = DatasetManager.selectedBand;
    
    // Include min/max visualization parameters
    const minInput = document.getElementById('minValue');
    const maxInput = document.getElementById('maxInput');
    
    if (minInput && maxInput) {
      params.visualization = {
        band: DatasetManager.selectedBand,
        colormap: DatasetManager.selectedColormap,
        min: parseFloat(minInput.value),
        max: parseFloat(maxInput.value)
      };
      
      console.log("Including visualization parameters in value query:", params.visualization);
    }
  }
  
  // API endpoint
  const endpoint = '/get_value_at_location';
  
  console.log("Sending value query with params:", params);
  
  // Show loading message in popup while fetching
  this.infoPopup
    .setLatLng(latlng)
    .setContent('<div class="popup-loading">Loading value information...</div>')
    .openOn(this.map);
  
  fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(params)
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      this.infoPopup.setContent(`<div class="popup-error">Error: ${data.error}</div>`);
      return;
    }
    
    // Display the value information
    this.displayValueInfo(data, latlng, isFeatureCollection);
  })
  .catch(err => {
    console.error("Error fetching value information:", err);
    this.infoPopup.setContent('<div class="popup-error">Failed to retrieve value information</div>');
  });
},


/**
 * Initialize right-click listener for value inspection
 */
initValueInspection: function() {
  // Add a popup for displaying values
  this.infoPopup = L.popup({
    className: 'value-info-popup',
    closeButton: true,
    autoClose: true,
    closeOnEscapeKey: true
  });
  
  // Add context menu (right-click) listener
  this.map.on('contextmenu', (e) => {
    // Only proceed if we have an overlay layer
    if (!this.overlayLayer) {
      return;
    }
    
    // Show loading in the popup while we fetch data
    this.infoPopup
      .setLatLng(e.latlng)
      .setContent('<div class="popup-loading">Loading value information...</div>')
      .openOn(this.map);
    
    // Get the pixel/feature value at this location
    this.getValueAtLocation(e.latlng);
  });

  // Add click listener to close the popup when clicking elsewhere on the map
  this.map.on('click', () => {
    this.map.closePopup(this.infoPopup);
  });
  
  console.log("Value inspection initialized (right-click on map to query values)");
},



/**
 * Display value information in a popup
 * @param {Object} data - Value data from the API
 * @param {L.LatLng} latlng - The click location
 * @param {boolean} isFeatureCollection - Whether this is a feature collection
 */
displayValueInfo: function(data, latlng, isFeatureCollection) {
  let content = '<div class="popup-content">';
  
  // Add location information
  content += `<div class="popup-header">
    <strong>Location:</strong> ${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}
  </div>`;
  
  // For feature collections, display attributes
  if (isFeatureCollection && data.features && data.features.length > 0) {
    content += '<div class="popup-section"><strong>Feature Properties:</strong></div>';
    content += '<table class="popup-attributes">';
    
    // Get the first feature's properties
    const properties = data.features[0].properties;
    
    // Sort properties alphabetically for better readability
    const sortedKeys = Object.keys(properties).sort();
    
    for (const key of sortedKeys) {
      const value = properties[key];
      // Skip system properties and null values
      if (key.startsWith('system:') || value === null || value === undefined) continue;
      
      content += `<tr>
        <td class="attribute-name">${key}</td>
        <td class="attribute-value">${value}</td>
      </tr>`;
    }
    
    content += '</table>';
    
    // If there are multiple features, add a note
    if (data.features.length > 1) {
      content += `<div class="popup-note">${data.features.length} features found at this location. Showing the first one.</div>`;
    }
  } 
  // For image/image collections, display band values
  else if (data.values) {
    // Get dataset title for display
    let datasetTitle = '';
    if (DatasetManager.currentDatasetInfo && DatasetManager.currentDatasetInfo.title) {
      datasetTitle = DatasetManager.currentDatasetInfo.title;
    } else if (DatasetManager.currentDataset) {
      datasetTitle = DatasetManager.currentDataset.split('/').pop();
    }
    
    // If we have a title, show it in the popup
    if (datasetTitle) {
      content += `<div class="popup-section"><strong>${datasetTitle}</strong></div>`;
    }
    
    // Show band values
    content += '<div class="popup-section"><strong>Band Values:</strong></div>';
    content += '<table class="popup-attributes">';
    
    // Get the current dataset info to help with formatting
    const datasetInfo = DatasetManager.currentDatasetInfo;
    let bandInfo = {};
    
    // Try to get band descriptions if available
    if (datasetInfo && datasetInfo.summaries && datasetInfo.summaries['eo:bands']) {
      const bands = datasetInfo.summaries['eo:bands'];
      bands.forEach(band => {
        if (band.name) {
          bandInfo[band.name] = {
            description: band.description || band.name,
            units: band.unit || ''
          };
        }
      });
    }
    
    // Add common band descriptions
    const commonBands = {
      'NDVI': { description: 'Normalized Difference Vegetation Index', units: 'Index (-1 to 1)' },
      'EVI': { description: 'Enhanced Vegetation Index', units: 'Index' }
    };
    
    // Merge common bands with dataset-specific bands
    Object.keys(commonBands).forEach(band => {
      if (!bandInfo[band]) {
        bandInfo[band] = commonBands[band];
      }
    });
    
    // Sort band names alphabetically to ensure consistent order
    const sortedBands = Object.keys(data.values).sort();
    
    // Process and display each band value
    for (const band of sortedBands) {
      const value = data.values[band];
      
      // Skip system properties and null values
      if (band.startsWith('system:') || value === null || value === undefined) continue;
      
      let displayValue = value;
      let displayBand = band;
      
      // Format the value properly
      if (typeof value === 'number') {
        // Determine appropriate precision based on the value
        if (Math.abs(value) < 0.01) {
          displayValue = value.toExponential(2);
        } else if (Math.abs(value) < 1) {
          displayValue = value.toFixed(4);
        } else if (Math.abs(value) < 10) {
          displayValue = value.toFixed(2);
        } else if (value % 1 === 0) {
          displayValue = value;  // Integer
        } else {
          displayValue = value.toFixed(2);
        }
        
        // Add units if known
        if (bandInfo[band] && bandInfo[band].units) {
          displayValue += ' ' + bandInfo[band].units;
        }
      } else if (value === null || value === undefined) {
        displayValue = 'No Data';
      }
      
      // Use band description if available
      if (bandInfo[band] && bandInfo[band].description) {
        displayBand = bandInfo[band].description;
      }
      
      content += `<tr>
        <td class="attribute-name">${displayBand}</td>
        <td class="attribute-value">${displayValue}</td>
      </tr>`;
    }
    
    content += '</table>';
    
    // Add temporal context information
    let temporalInfo = '';
    
    // Show date information if available from API response
    if (data.date) {
      if (data.date.includes(' to ')) {
        // Date range (from aggregation)
        temporalInfo += `<div>Time period: ${data.date}</div>`;
        
        // Add aggregation method if available
        if (data.aggregation) {
          temporalInfo += `<div>Method: ${data.aggregation} composite</div>`;
        }
      } else {
        // Single date (from specific image)
        temporalInfo += `<div>Image date: ${data.date}</div>`;
      }
    }
    
    // Add information about the active temporal filter
    if (DatasetManager.temporalSelection && DatasetManager.temporalSelection.isTemporalDataset) {
      const year = DatasetManager.temporalSelection.year;
      const month = DatasetManager.temporalSelection.month;
      const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
      ];
      const monthName = monthNames[month - 1];
      
      if (!temporalInfo) {
        temporalInfo += `<div>Time filter: ${monthName} ${year}</div>`;
      }
    }
    
    // If we have temporal info, add it to the popup
    if (temporalInfo) {
      content += `<div class="popup-note">${temporalInfo}</div>`;
    }
  } else {
    content += '<div class="popup-error">No data found at this location</div>';
    
    // Add helpful message for common issues
    content += `<div class="popup-note">
      <p>This could be due to:</p>
      <ul style="margin-top: 5px; padding-left: 20px;">
        <li>No data available in the current time period</li>
        <li>The location is outside the dataset's coverage area</li>
      </ul>
      <p style="margin-top: 5px;">Try a different location or time period.</p>
    </div>`;
  }
  
  content += '</div>';
  
  // Update the popup with the content
  this.infoPopup.setContent(content);
},
  
  /**
   * Add opacity and zoom controls to map controls panel
   */
  addControls: function() {
    const controlsDiv = document.querySelector('.map-controls');
    
    if (controlsDiv) {
      // Create the container for opacity and zoom controls
      const controlsHTML = `
        <div class="map-opacity-zoom-container">
          <div class="map-opacity-control">
            <label for="mapOpacitySlider">Layer Opacity</label>
            <input type="range" id="mapOpacitySlider" min="0" max="1" step="0.05" value="${this.currentOpacity}">
            <div class="map-opacity-value" id="mapOpacityValue">${Math.round(this.currentOpacity * 100)}%</div>
          </div>
          
          <div class="map-zoom-control">
            <button id="zoomInBtn" class="zoom-btn" title="Zoom In">+</button>
            <button id="zoomOutBtn" class="zoom-btn" title="Zoom Out">−</button>
          </div>
        </div>
      `;
      
      // Append the controls to the map controls div
      controlsDiv.insertAdjacentHTML('beforeend', controlsHTML);
      
      // Add opacity slider event listener
      document.getElementById('mapOpacitySlider').addEventListener('input', (e) => {
        const opacity = parseFloat(e.target.value);
        this.setOverlayOpacity(opacity);
        
        // Update the displayed percentage value
        const opacityPercent = Math.round(opacity * 100);
        document.getElementById('mapOpacityValue').textContent = opacityPercent + '%';
        
        // Log updated opacity for debugging
        console.log(`Layer opacity set to ${opacity} (${opacityPercent}%)`);
      });
      
      // Add zoom button listeners
      document.getElementById('zoomInBtn').addEventListener('click', () => {
        this.map.zoomIn();
      });
      
      document.getElementById('zoomOutBtn').addEventListener('click', () => {
        this.map.zoomOut();
      });
    }
  },
  
  /**
   * Log map information to console for debugging
   */
  logMapDebugInfo: function() {
    const center = this.map.getCenter();
    const zoom = this.map.getZoom();
    
    console.log("=== MAP DEBUG INFO ===");
    console.log(`Current Dataset: ${DatasetManager.currentDataset || 'None'}`);
    console.log(`Map Center: [${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}]`);
    console.log(`Zoom Level: ${zoom}`);
    console.log(`Basemap: ${this.currentBasemap}`);
    console.log(`Overlay Opacity: ${this.currentOpacity}`);
    console.log("=======================");
  },
  
  /**
   * Switch basemaps
   * @param {string} mapType - Type of basemap ('dark', 'light', or 'satellite')
   */
  switchBasemap: function(mapType) {
    // Remove current basemap
    if (this.currentBasemap === 'dark') this.map.removeLayer(this.darkBasemap);
    else if (this.currentBasemap === 'light') this.map.removeLayer(this.lightBasemap);
    else if (this.currentBasemap === 'satellite') this.map.removeLayer(this.satelliteBasemap);
    
    // Update current basemap type
    this.currentBasemap = mapType;
    
    // Add new basemap
    if (mapType === 'dark') {
      this.darkBasemap.addTo(this.map);
      // Update button states
      document.getElementById('darkMapBtn').classList.add('active');
      document.getElementById('lightMapBtn').classList.remove('active');
      document.getElementById('satelliteBtn').classList.remove('active');
    } else if (mapType === 'light') {
      this.lightBasemap.addTo(this.map);
      // Update button states
      document.getElementById('lightMapBtn').classList.add('active');
      document.getElementById('darkMapBtn').classList.remove('active');
      document.getElementById('satelliteBtn').classList.remove('active');
    } else if (mapType === 'satellite') {
      this.satelliteBasemap.addTo(this.map);
      // Update button states
      document.getElementById('satelliteBtn').classList.add('active');
      document.getElementById('darkMapBtn').classList.remove('active');
      document.getElementById('lightMapBtn').classList.remove('active');
    }
    
    // Ensure the overlay is still on top after basemap change
    if (this.overlayLayer) {
      this.map.removeLayer(this.overlayLayer);
      this.overlayLayer.addTo(this.map);
    }
    
    // Log basemap change for debugging
    console.log(`Switched basemap to: ${mapType}`);
  },
  
  /**
   * Set map view or bounds based on dataset properties
   * @param {Object} data - Dataset response with map positioning data
   */
  setMapView: function(data) {
    // Track whether we've successfully positioned the map
    let mapPositioned = false;
    console.log("=== MAP POSITIONING DEBUG ===");
    
    // First priority: JS map center (most reliable)
    if (data.js_map_center && 
        typeof data.js_map_center.lat === 'number' && 
        typeof data.js_map_center.lon === 'number') {
        
        console.log("USING JS MAP CENTER for positioning");
        const zoom = data.js_map_center.zoom || 8;  // Default to zoom 8 if not specified
        this.map.setView([data.js_map_center.lat, data.js_map_center.lon], zoom);
        console.log(`Set view to lat: ${data.js_map_center.lat}, lon: ${data.js_map_center.lon}, zoom: ${zoom}`);
        mapPositioned = true;
    }
    // Second priority: lookat parameters
    else if (data.lookat && 
             typeof data.lookat.lat === 'number' && 
             typeof data.lookat.lon === 'number') {
             
        console.log("USING LOOKAT for positioning");
        const lookAtZoom = data.lookat.zoom || 5;
        this.map.setView([data.lookat.lat, data.lookat.lon], lookAtZoom);
        console.log(`Set view to lat: ${data.lookat.lat}, lon: ${data.lookat.lon}, zoom: ${lookAtZoom}`);
        mapPositioned = true;
    }
    // Last priority: bounding box with validation
    else if (data.bbox && Array.isArray(data.bbox)) {
        console.log("USING BBOX for positioning");
        
        const fixedBbox = Utils.validateAndFixBbox(data.bbox);
        
        if (fixedBbox) {
            console.log("Using validated bbox for map positioning:", fixedBbox);
            try {
                const bounds = [
                    [fixedBbox[1], fixedBbox[0]], // Southwest corner [lat, lng]
                    [fixedBbox[3], fixedBbox[2]]  // Northeast corner [lat, lng]
                ];
                
                // Check if the bounds are valid (not just points and not covering the whole world)
                const isValidBounds = 
                    fixedBbox[0] !== fixedBbox[2] && 
                    fixedBbox[1] !== fixedBbox[3] &&
                    Math.abs(fixedBbox[0] - fixedBbox[2]) < 360 &&
                    Math.abs(fixedBbox[1] - fixedBbox[3]) < 170;
                
                if (isValidBounds) {
                    this.map.fitBounds(bounds);
                    console.log(`Set bounds to SW: [${bounds[0]}], NE: [${bounds[1]}]`);
                    mapPositioned = true;
                } else {
                    console.warn("Bbox creates invalid bounds, falling back to default view");
                }
            } catch (e) {
                console.error("Error setting map bounds:", e);
            }
        }
    }
    
    // If all positioning methods failed, use default view
    if (!mapPositioned) {
        console.warn("No valid positioning data found, using default global view");
        this.map.setView([0, 0], 2);
    }
  },
  
  /**
   * Add a tile layer overlay to the map
   * @param {string} tileUrl - URL template for the tile layer
   */
  addOverlayLayer: function(tileUrl) {
    // Remove any existing overlay layer
    if (this.overlayLayer) {
      this.map.removeLayer(this.overlayLayer);
    }
    
    // Add GEE tiles with proper pane setting to ensure it displays above the basemap
    this.overlayLayer = L.tileLayer(tileUrl, { 
      opacity: this.currentOpacity,
      // Use a transparent pixel for error tiles
      errorTileUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
      pane: 'overlayPane',
      zIndex: 400, // Make sure it's above the basemap
      tms: false,  // GEE doesn't use TMS
      maxNativeZoom: 14, // Prevent requesting too high zoom levels
      maxZoom: 19 // Allow UI zoom beyond native tiles
    });
    
    // Add the layer to the map
    this.overlayLayer.addTo(this.map);
    
    // Update the opacity slider value in the map controls
    const mapOpacitySlider = document.getElementById('mapOpacitySlider');
    if (mapOpacitySlider) {
      mapOpacitySlider.value = this.currentOpacity;
    }
    
    // Update the opacity percentage display
    const mapOpacityValue = document.getElementById('mapOpacityValue');
    if (mapOpacityValue) {
      mapOpacityValue.textContent = Math.round(this.currentOpacity * 100) + '%';
    }
    
    console.log(`Added overlay layer with URL pattern: ${tileUrl}`);
  },
  
  /**
   * Set the opacity of the current overlay layer
   * @param {number} opacity - Opacity value (0-1)
   */
  setOverlayOpacity: function(opacity) {
    if (this.overlayLayer) {
      this.currentOpacity = opacity;
      this.overlayLayer.setOpacity(opacity);
    }
  }
};