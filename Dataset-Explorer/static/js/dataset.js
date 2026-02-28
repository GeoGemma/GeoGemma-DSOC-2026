/**
 * Dataset loading and management
 */
const DatasetManager = {
  // The current loaded dataset ID
  currentDataset: null,
  // Dataset metadata from search results
  currentDatasetInfo: null,
  // Flag to initialize style controls after rendering
  initStyleControlsAfterRender: false,
  // Available bands for the current dataset
  availableBands: [],
  // Currently selected band
  selectedBand: null,
  // Currently selected colormap
  selectedColormap: 'terrain',
  // Available colormaps
  availableColormaps: [
    { id: 'terrain', name: 'Terrain', colors: ['#0A42A5', '#00D300', '#FFFF00', '#FF8C00', '#A52A2A', '#FFFFFF'] },
    { id: 'jet', name: 'Jet', colors: ['#000080', '#0000FF', '#00FFFF', '#FFFF00', '#FF0000', '#800000'] },
    { id: 'plasma', name: 'Plasma', colors: ['#0D0887', '#5B02A3', '#9A179B', '#CB4678', '#EB7852', '#FDB32F', '#F0F921'] },
    { id: 'blues', name: 'Blues', colors: ['#F7FBFF', '#D0D1E6', '#A6BDDB', '#74A9CF', '#3690C0', '#0570B0', '#034E7B'] },
    { id: 'greens', name: 'Greens', colors: ['#F7FCF5', '#C7E9C0', '#A1D99B', '#74C476', '#41AB5D', '#238B45', '#005A32'] }
  ],
  // Time selection for temporal datasets
  temporalSelection: {
    year: new Date().getFullYear(),  // Default to current year
    month: new Date().getMonth() + 1,  // Default to current month (1-12)
    isTemporalDataset: false
  },
  // Store dataset's temporal range for reference
  temporalDateRange: null,
  
/**
 * Load a dataset by ID
 * @param {string} datasetId - The ID of the dataset to load
 * @param {boolean} retry - Whether this is a retry attempt
 * @param {Object} datasetInfo - The dataset metadata from search results (optional)
 */
loadDataset: function(datasetId, retry = false, datasetInfo = null) {
  // Store the dataset metadata if provided
  if (datasetInfo) {
    this.currentDatasetInfo = datasetInfo;
  }
  
  // Show loading indicator
  Utils.showLoading();
  
  // Make left panel visible
  const leftPanel = document.getElementById('leftPanel');
  leftPanel.style.display = "block";
  leftPanel.innerHTML = "<h4>Loading Dataset</h4><p>Retrieving information and generating tiles...</p>";
  
  // Save current dataset ID
  this.currentDataset = datasetId;
  
  // Reset the temporal date range when loading a new dataset
  this.temporalDateRange = null;
  
  // Update debug info
  UI.updateDebugInfo();
  
  // Prepare special parameters for certain datasets
  let extraParams = {};
  
  // For Feature Collections like Open Buildings, we might need special handling
  if (datasetId.includes('open-buildings')) {
    console.log("Using special handling for Open Buildings dataset");
    
    // If this is a retry, use more aggressive limiting
    if (retry) {
      extraParams.limit_features = 1000;
      extraParams.skip_confidence_filter = true;
    }
    
    // For buildings, make sure we switch to satellite basemap
    MapManager.switchBasemap('satellite');
  }
  
  // Check if this dataset is a likely temporal dataset
  this.temporalSelection.isTemporalDataset = this.isLikelyTemporalDataset(datasetId);
  
  fetch('/get_tile', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ 
      dataset_id: datasetId,
      ...extraParams
    })
  })
  .then(response => response.json())
  .then(data => {
    Utils.hideLoading();
    
    // Debug: inspect the dataset response
    Utils.inspectDatasetResponse(data);
    
    // Store date range for future reference if available
    if (data.date_range && Array.isArray(data.date_range) && data.date_range.length === 2) {
      this.temporalDateRange = data.date_range;
    }
    
    // If js_visualization_info is in the response, store it in currentDatasetInfo
    if (data.js_visualization_info && typeof data.js_visualization_info === 'object') {
      if (!this.currentDatasetInfo) {
        this.currentDatasetInfo = {};
      }
      this.currentDatasetInfo.js_visualization_info = data.js_visualization_info;
      
      // Debug: log if default temporal filter info is available
      if (data.js_visualization_info.temporal_filter) {
        console.log("Found default temporal filter information:", data.js_visualization_info.temporal_filter);
      }
    }
    
    // If js_map_center is in the response, store it too
    if (data.js_map_center && typeof data.js_map_center === 'object') {
      if (!this.currentDatasetInfo) {
        this.currentDatasetInfo = {};
      }
      this.currentDatasetInfo.js_map_center = data.js_map_center;
    }
    
    if (data.error) {
      this.handleDatasetError(data.error, datasetId, retry);
    } else {
      // Extract and store available bands
      this.processDatasetBands(data);
      this.renderDataset(data, datasetId);
    }
  })
  .catch(err => {
    Utils.hideLoading();
    console.error("Error loading dataset:", err);
    document.getElementById('leftPanel').innerHTML = 
      "<h4>Connection Error</h4>" +
      "<p>Failed to connect to the server or process the dataset.</p>" +
      "<p>See console for details.</p>";
  });
},
  
  /**
   * Check if a dataset is likely to be a temporal dataset based on ID
   * @param {string} datasetId - The dataset ID
   * @returns {boolean} - Whether it's likely a temporal dataset
   */
  isLikelyTemporalDataset: function(datasetId) {
    const temporalKeywords = [
      'LANDSAT', 'SENTINEL', 'MODIS', 'VIIRS', 'ERA5', 'GOES', 
      'TROPOMI', 'GLDAS', 'COPERNICUS', 'ECMWF', 'GRIDMET', 
      'CHIRPS', 'AGERA5', 'IMERG', 'JAXA'
    ];
    
    // Check if any of the temporal keywords are in the dataset ID
    return temporalKeywords.some(keyword => datasetId.includes(keyword));
  },
  
  /**
   * Process and store available bands from dataset response
   * @param {Object} data - Dataset response data
   */
  processDatasetBands: function(data) {
    // Reset available bands
    this.availableBands = [];
    this.selectedBand = null;
    
    // Check if bands are available in the dataset info first (most detailed source)
    if (this.currentDatasetInfo && 
        this.currentDatasetInfo.summaries && 
        this.currentDatasetInfo.summaries['eo:bands'] && 
        Array.isArray(this.currentDatasetInfo.summaries['eo:bands'])) {
      
      const bandsWithDetails = this.currentDatasetInfo.summaries['eo:bands'];
      console.log("Bands from dataset metadata:", bandsWithDetails);
      
      // Extract full band information including name, description, wavelength, gsd
      this.availableBands = bandsWithDetails.map(bandInfo => ({
        name: bandInfo.name,
        description: bandInfo.description || '',
        center_wavelength: bandInfo.center_wavelength,
        gsd: bandInfo.gsd, // Ground sampling distance
        min: bandInfo.min !== undefined ? bandInfo.min : 0,
        max: bandInfo.max !== undefined ? bandInfo.max : 3000
      }));
      
      console.log("Processed bands with full metadata:", this.availableBands);
    } 
    // Fallback to simple band names from data response
    else if (data.bands && Array.isArray(data.bands) && data.bands.length > 0) {
      console.log("Using simple band names from data response:", data.bands);
      
      // Convert simple band names to objects
      this.availableBands = data.bands.map(bandName => ({
        name: bandName,
        description: '',
        min: 0,
        max: 3000
      }));
    }
    
    // Set first band as selected by default if bands are available
    if (this.availableBands.length > 0) {
      this.selectedBand = this.availableBands[0].name;
      console.log("Selected band:", this.selectedBand);
    }
  },
  
  /**
   * Handle dataset loading errors
   * @param {string} error - Error message
   * @param {string} datasetId - Dataset ID that caused the error
   * @param {boolean} retry - Whether this was already a retry attempt
   */
  handleDatasetError: function(error, datasetId, retry) {
    console.error("Dataset loading error:", error);
    
    // Special handling for common errors
    if (error.includes("Expected asset") && error.includes("to be an ImageCollection")) {
      document.getElementById('leftPanel').innerHTML = 
        "<h4>Dataset Error</h4>" +
        "<p>This dataset is not compatible with the current visualization method.</p>" +
        "<p><strong>Error details:</strong> " + error + "</p>" +
        "<p>This typically happens with Feature Collections and Tables.</p>";
    } 
    else if (error.includes("open-buildings") && !retry) {
      // For Open Buildings specifically, we can retry with more limiting
      document.getElementById('leftPanel').innerHTML = 
        "<h4>Retrying with Limits</h4>" +
        "<p>The Open Buildings dataset is very large. Retrying with stricter limits...</p>";
      
      // Wait a second then retry with special handling
      setTimeout(() => {
        this.loadDataset(datasetId, true);
      }, 1000);
    }
    else {
      document.getElementById('leftPanel').innerHTML = 
        "<h4>Dataset Error</h4>" +
        "<p>An error occurred while loading this dataset:</p>" +
        "<p><strong>" + error + "</strong></p>";
    }
  },
  
  /**
   * Render a successfully loaded dataset
   * @param {Object} data - Dataset response data
   * @param {string} datasetId - Dataset ID
   */
  renderDataset: function(data, datasetId) {
    var tileUrl = data.tileUrl;
    
    try {
      // Debug palette data received from server
      console.log("=== PALETTE DEBUG INFO ===");
      console.log("Dataset ID:", datasetId);
      console.log("Has palette data:", !!data.palette);
      if (data.palette) {
        console.log("Palette type:", typeof data.palette);
        console.log("Palette is array:", Array.isArray(data.palette));
        console.log("Palette length:", data.palette.length);
        console.log("Palette values:", data.palette);
      }
      console.log("Min value:", data.min);
      console.log("Max value:", data.max);
      console.log("Has class descriptions:", !!data.class_descriptions);
      if (data.class_descriptions) {
        console.log("Class desc type:", typeof data.class_descriptions);
        console.log("Class desc is array:", Array.isArray(data.class_descriptions));
        console.log("Class desc length:", data.class_descriptions.length);
        console.log("First class desc item:", data.class_descriptions[0]);
      }
      console.log("==========================");
      
      // Add the tile layer to the map
      MapManager.addOverlayLayer(tileUrl);
      
      // Set appropriate basemap based on dataset type
      if (data.is_feature_collection) {
        // For administrative boundaries, use a light basemap
        if (datasetId.includes('boundaries') || datasetId.includes('admin')) {
          MapManager.switchBasemap('light');
        } else {
          MapManager.switchBasemap('satellite'); // Switch to satellite for other features
        }
      } else if (!datasetId.includes('open-buildings')) {
        // Only switch to dark if not buildings (we already switched for buildings earlier)
        if (MapManager.currentBasemap !== 'dark') {
          MapManager.switchBasemap('dark'); // Switch to dark basemap
        }
      }
      
      // Set map view based on dataset spatial information
      MapManager.setMapView(data);
      
      // Update debug info
      UI.updateDebugInfo();
      
      // Update the left panel with available information
      this.updateLeftPanel(data, datasetId);
      
    } catch (e) {
      Utils.hideLoading();
      console.error("Error rendering dataset:", e);
      document.getElementById('leftPanel').innerHTML = 
        "<h4>Rendering Error</h4>" +
        "<p>Failed to render the dataset on the map:</p>" +
        "<p><strong>" + e.message + "</strong></p>" +
        "<p>Please try a different dataset or refresh the page.</p>";
    }
  },
  
/**
 * Update the left panel with dataset information
 * @param {Object} data - Dataset response data
 * @param {string} datasetId - Dataset ID
 */
updateLeftPanel: function(data, datasetId) {
  var leftPanel = document.getElementById('leftPanel');
  var panelContent = "";
  
  // Make sure left panel is visible
  leftPanel.style.display = "block";
  
  // Add dataset title if available
  if (this.currentDatasetInfo && this.currentDatasetInfo.title) {
    panelContent += `<h3>${this.currentDatasetInfo.title}</h3>`;
  } else {
    panelContent += `<h3>${datasetId}</h3>`;
  }
  
  // Add dataset description if available with Wikipedia links
  if (this.currentDatasetInfo && this.currentDatasetInfo.description) {
    // Process the description with our wiki link utility
    const descriptionWithLinks = WikiLinkUtility.addWikipediaLinks(this.currentDatasetInfo.description);
    
    panelContent += `<div class="dataset-description">
      <h4>Description</h4>
      <p>${descriptionWithLinks}</p>
      
    </div>`;
  }
  
  // Add temporal availability if available
  if (this.currentDatasetInfo && 
      this.currentDatasetInfo.extent && 
      this.currentDatasetInfo.extent.temporal && 
      this.currentDatasetInfo.extent.temporal.interval && 
      this.currentDatasetInfo.extent.temporal.interval.length > 0) {
    
    let startDate = this.currentDatasetInfo.extent.temporal.interval[0][0];
    let endDate = this.currentDatasetInfo.extent.temporal.interval[0][1];
    
    // Extract just the years
    let startYear = startDate ? startDate.substring(0, 4) : "N/A";
    let endYear = endDate ? endDate.substring(0, 4) : "Present";
    
    panelContent += `<div class="dataset-temporal">
      <h4>Temporal Availability</h4>
      <p>${startYear} - ${endYear}</p>
    </div>`;
  } else if (data.date_range && Array.isArray(data.date_range) && data.date_range.length === 2) {
    // Alternative date source from data response
    let startDate = data.date_range[0];
    let endDate = data.date_range[1];
    
    // Extract just the years
    let startYear = startDate ? startDate.substring(0, 4) : "N/A";
    let endYear = endDate ? endDate.substring(0, 4) : "Present";
    
    panelContent += `<div class="dataset-temporal">
      <h4>Temporal Availability</h4>
      <p>${startYear} - ${endYear}</p>
    </div>`;
  }
  
  // Add dataset link if available
  // First check for links[1].href path
  if (this.currentDatasetInfo && this.currentDatasetInfo.links && 
      Array.isArray(this.currentDatasetInfo.links) && 
      this.currentDatasetInfo.links.length > 1 && 
      this.currentDatasetInfo.links[1].href) {
      
    const datasetLink = this.currentDatasetInfo.links[1].href;
    panelContent += `<div class="dataset-links">
      <h4>Dataset Link</h4>
      <ul>
        <li><a href="${datasetLink}" target="_blank">View Dataset</a></li>
      </ul>
    </div>`;
  }
  // Fallback to the previous path structure if exists
  else if (this.currentDatasetInfo && this.currentDatasetInfo.links && 
      Array.isArray(this.currentDatasetInfo.links.related)) {
    panelContent += `<div class="dataset-links">
      <h4>Related Links</h4>
      <ul>`;
    
    this.currentDatasetInfo.links.related.forEach(link => {
      if (link.href) {
        panelContent += `<li><a href="${link.href}" target="_blank">${link.title || 'Resource'}</a></li>`;
      }
    });
    
    panelContent += `</ul></div>`;
  }
  
  // Add palette visualization if available - MOVED HERE right after dataset links
  if (data.palette && Array.isArray(data.palette) && data.palette.length > 0) {
    console.log("Adding palette visualization to panel");
    
    // Process palette to ensure colors have # prefix
    const processedPalette = data.palette.map(color => {
      if (typeof color === 'string' && !color.startsWith('#') && 
          /^[0-9A-Fa-f]{6}$/.test(color)) {
        return '#' + color;
      }
      return color;
    });
    
    // Process class descriptions if available
    let processedClassDesc = null;
    if (data.class_descriptions && Array.isArray(data.class_descriptions) && 
        data.class_descriptions.length > 0) {
      
      processedClassDesc = data.class_descriptions.map(cls => {
        if (cls && cls.color && typeof cls.color === 'string' && 
            !cls.color.startsWith('#') && /^[0-9A-Fa-f]{6}$/.test(cls.color)) {
          // Make a copy of the object to avoid modifying the original
          return {...cls, color: '#' + cls.color};
        }
        return cls;
      });
    }
    
    // Add palette visualization to the panel - pass datasetId to help determine units
    // Removed the duplicate "Color Palette" heading since it's already in the utility function
    panelContent += `<div class="palette-section">
      ${Utils.createPaletteDisplay(processedPalette, data.min, data.max, processedClassDesc, datasetId)}
    </div>`;
  }
  
  // Add default temporal filter info if available from js_visualization_info
  if (this.currentDatasetInfo && 
      this.currentDatasetInfo.js_visualization_info && 
      this.currentDatasetInfo.js_visualization_info.temporal_filter) {
    
    const tempFilter = this.currentDatasetInfo.js_visualization_info.temporal_filter;
    
    if (tempFilter.start_date && tempFilter.end_date) {
      // Format the dates for display
      const startDate = new Date(tempFilter.start_date);
      const endDate = new Date(tempFilter.end_date);
      
      // Format the dates in a readable way
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      const formattedStartDate = startDate.toLocaleDateString(undefined, options);
      const formattedEndDate = endDate.toLocaleDateString(undefined, options);
      
      panelContent += `<div class="default-temporal-filter">
        <h4>Default Temporal Filter</h4>
        <p>This dataset has a default temporal filter from ${formattedStartDate} to ${formattedEndDate}</p>
      </div>`;
    }
  } else if (data.js_visualization_info && 
             data.js_visualization_info.temporal_filter) {
    
    // Alternative: Get from the data response if available
    const tempFilter = data.js_visualization_info.temporal_filter;
    
    if (tempFilter.start_date && tempFilter.end_date) {
      // Format the dates for display
      const startDate = new Date(tempFilter.start_date);
      const endDate = new Date(tempFilter.end_date);
      
      // Format the dates in a readable way
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      const formattedStartDate = startDate.toLocaleDateString(undefined, options);
      const formattedEndDate = endDate.toLocaleDateString(undefined, options);
      
      panelContent += `<div class="default-temporal-filter">
        <h4>Default Temporal Filter</h4>
        <p>This dataset has a default temporal filter from ${formattedStartDate} to ${formattedEndDate}</p>
        <p class="temporal-source">This is the default time range used for visualization</p>
      </div>`;
    }
  }
  
  // For Feature Collections, show style controls and different info
  if (data.is_feature_collection) {
    // Add feature style controls for any feature collection
    panelContent += this.createFeatureStyleControls();
    this.initStyleControlsAfterRender = true;
    
    panelContent += "<h4>Feature Collection</h4>";
    panelContent += "<p>This dataset contains vector features. Use the style controls above to customize the appearance.</p>";
    
    if (data.feature_properties && data.feature_properties.length > 0) {
      panelContent += "<h4>Available Properties</h4><ul>";
      data.feature_properties.forEach(function(prop) {
        panelContent += "<li>" + prop + "</li>";
      });
      panelContent += "</ul>";
    }
    
    // For building dataset, show specific info
    if (datasetId.includes('open-buildings')) {
      panelContent += "<div style='background-color: #f8f9fa; padding: 10px; border-left: 4px solid #28a745; margin-bottom: 15px;'>" +
        "<strong>Open Buildings Dataset</strong><br>" +
        "This dataset shows building footprints derived from satellite imagery. " +
        "Buildings are filtered to show only those with confidence >= 0.65.</div>";
    }
  } else {
    // For image collections, add band selection FIRST (moved above temporal selection)
    panelContent += this.createBandSelectionControls();
    
    // Then add temporal selection if applicable (moved below band visualization)
    if (this.temporalSelection.isTemporalDataset) {
      panelContent += this.createTemporalSelectionControls();
    }
  }
  
  // Log debug information to console instead of showing it in the panel
  console.log("=== DATASET DEBUG INFO ===");
  if (data.bbox) {
    console.log(`Bounding Box: [${data.bbox.join(', ')}]`);
  } else {
    console.log("Bounding Box: Not available");
  }
  
  if (data.lookat) {
    console.log(`Look At: lat=${data.lookat.lat}, lon=${data.lookat.lon}, zoom=${data.lookat.zoom}`);
  } else {
    console.log("Look At: Not available");
  }
  
  if (data.js_map_center) {
    console.log(`JS Map Center: lat=${data.js_map_center.lat}, lon=${data.js_map_center.lon}, zoom=${data.js_map_center.zoom || 'N/A'}`);
  } else {
    console.log("JS Map Center: Not available");
  }
  
  console.log(`Dataset ID: ${datasetId}`);
  console.log(`Current Basemap: ${MapManager.currentBasemap}`);
  console.log("===========================");
  
  // Set the panel content
  leftPanel.innerHTML = panelContent;
  
  // Initialize feature style controls if needed
  if (this.initStyleControlsAfterRender) {
    this.initFeatureStyleControls(datasetId);
    this.initStyleControlsAfterRender = false;
  }
  
  // Initialize temporal selection controls if dataset is temporal
  if (this.temporalSelection.isTemporalDataset) {
    this.initTemporalSelectionControls(datasetId);
  }
  
  // Initialize band selection controls if available
  if (this.availableBands && this.availableBands.length > 0 && !data.is_feature_collection) {
    this.initBandSelectionControls(datasetId);
  }
},
  
  /**
   * Create UI controls for temporal selection
   * @returns {string} HTML for temporal selection controls
   */
  createTemporalSelectionControls: function() {
    // Get the dataset's temporal range if available
    let startYear = 1980;
    let endYear = new Date().getFullYear();
    
    // If we have current dataset info with temporal extent, use it
    if (this.currentDatasetInfo && 
        this.currentDatasetInfo.extent && 
        this.currentDatasetInfo.extent.temporal && 
        this.currentDatasetInfo.extent.temporal.interval && 
        this.currentDatasetInfo.extent.temporal.interval.length > 0) {
        
      const interval = this.currentDatasetInfo.extent.temporal.interval[0];
      if (interval && interval.length >= 2) {
        // Extract year from the start date (format: YYYY-MM-DD...)
        if (interval[0] && typeof interval[0] === 'string' && interval[0].length >= 4) {
          const parsedYear = parseInt(interval[0].substring(0, 4));
          if (!isNaN(parsedYear)) {
            startYear = parsedYear;
            console.log(`Using dataset start year: ${startYear}`);
          }
        }
        
        // Extract year from the end date (format: YYYY-MM-DD...)
        if (interval[1] && typeof interval[1] === 'string' && interval[1].length >= 4) {
          // If end date is "present" or similar, use current year
          if (interval[1].toLowerCase().includes('present')) {
            endYear = new Date().getFullYear();
          } else {
            const parsedYear = parseInt(interval[1].substring(0, 4));
            if (!isNaN(parsedYear)) {
              endYear = parsedYear;
              console.log(`Using dataset end year: ${endYear}`);
            }
          }
        }
      }
    }
    // Alternative source: Check date_range from data response
    else if (this.temporalDateRange && Array.isArray(this.temporalDateRange) && this.temporalDateRange.length === 2) {
      // Extract year from start date
      if (this.temporalDateRange[0] && typeof this.temporalDateRange[0] === 'string' && this.temporalDateRange[0].length >= 4) {
        const parsedYear = parseInt(this.temporalDateRange[0].substring(0, 4));
        if (!isNaN(parsedYear)) {
          startYear = parsedYear;
          console.log(`Using date_range start year: ${startYear}`);
        }
      }
      
      // Extract year from end date
      if (this.temporalDateRange[1] && typeof this.temporalDateRange[1] === 'string' && this.temporalDateRange[1].length >= 4) {
        const parsedYear = parseInt(this.temporalDateRange[1].substring(0, 4));
        if (!isNaN(parsedYear) && parsedYear <= new Date().getFullYear()) {
          endYear = parsedYear;
          console.log(`Using date_range end year: ${endYear}`);
        }
      }
    }
    
    // Generate years from dataset's start year to end year
    const availableYears = [];
    for (let year = startYear; year <= endYear; year++) {
      availableYears.push(year);
    }
    
    // Create month names
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    // Get selected values (default to current date if within range, otherwise use end date)
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth() + 1;
    
    // Default to current year/month if within dataset range, otherwise use the most recent
    let selectedYear = (currentYear >= startYear && currentYear <= endYear) ? currentYear : endYear;
    let selectedMonth = (selectedYear === currentYear) ? currentMonth : 1;
    
    // Use stored values if already set
    if (this.temporalSelection.year && this.temporalSelection.year >= startYear && this.temporalSelection.year <= endYear) {
      selectedYear = this.temporalSelection.year;
    }
    if (this.temporalSelection.month && this.temporalSelection.month >= 1 && this.temporalSelection.month <= 12) {
      selectedMonth = this.temporalSelection.month;
    }
    
    // Update the current temporal selection
    this.temporalSelection.year = selectedYear;
    this.temporalSelection.month = selectedMonth;
    
    let html = `
      <div class="temporal-selection-controls">
        <h4>Temporal Selection</h4>
        <p class="temporal-description">Select a specific month and year to view a median mosaic for that time period.</p>
        
        <div class="temporal-control-row">
          <div class="control-group month-select">
            <label for="monthSelect">Month:</label>
            <select id="monthSelect" class="select-control">`;
    
    // Add month options
    monthNames.forEach((month, index) => {
      const monthValue = index + 1;  // 1-12
      const selected = monthValue === selectedMonth ? 'selected' : '';
      html += `<option value="${monthValue}" ${selected}>${month}</option>`;
    });
    
    html += `
            </select>
          </div>
          
          <div class="control-group year-select">
            <label for="yearSelect">Year:</label>
            <select id="yearSelect" class="select-control">`;
    
    // Add year options (most recent first)
    for (let i = availableYears.length - 1; i >= 0; i--) {
      const year = availableYears[i];
      const selected = year === selectedYear ? 'selected' : '';
      html += `<option value="${year}" ${selected}>${year}</option>`;
    }
    
    html += `
            </select>
          </div>
        </div>
        
        <button id="applyTemporalBtn" class="action-button">Apply Time Selection</button>
        
        <div class="temporal-range-info">
          Available range: ${startYear} - ${endYear}
        </div>
      </div>
    `;
    
    return html;
  },
  
  /**
   * Initialize the temporal selection controls
   * @param {string} datasetId - Current dataset ID
   */
  initTemporalSelectionControls: function(datasetId) {
    const yearSelect = document.getElementById('yearSelect');
    const monthSelect = document.getElementById('monthSelect');
    const applyTemporalBtn = document.getElementById('applyTemporalBtn');
    
    if (yearSelect && monthSelect && applyTemporalBtn) {
      // Listen for selection changes
      yearSelect.addEventListener('change', () => {
        this.temporalSelection.year = parseInt(yearSelect.value);
      });
      
      monthSelect.addEventListener('change', () => {
        this.temporalSelection.month = parseInt(monthSelect.value);
      });
      
      // Apply button click
      applyTemporalBtn.addEventListener('click', () => {
        this.applyTemporalSelection(datasetId);
      });
    }
  },
  
  /**
   * Apply the temporal selection and reload the dataset with new time filter
   * @param {string} datasetId - Current dataset ID
   */
  applyTemporalSelection: function(datasetId) {
    // Show loading indicator
    Utils.showLoading();
    
    const year = this.temporalSelection.year;
    const month = this.temporalSelection.month;
    
    console.log(`Applying temporal selection: Year=${year}, Month=${month}`);
    
    // Format month with leading zero if needed
    const monthFormatted = month < 10 ? `0${month}` : `${month}`;
    
    // Create date range for the selected month (1st to last day)
    const startDate = `${year}-${monthFormatted}-01`;
    
    // Get the last day of the month
    const lastDay = new Date(year, month, 0).getDate();
    const endDate = `${year}-${monthFormatted}-${lastDay}`;
    
    console.log(`Using date range: ${startDate} to ${endDate}`);
    
    // Prepare request parameters
    let requestParams = {
      dataset_id: datasetId,
      temporal_filter: {
        start_date: startDate,
        end_date: endDate,
        aggregation: 'median'  // Compute median mosaic
      }
    };
    
    // Make API request
    fetch('/get_tile', {
      method:'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestParams)
    })
    .then(response => response.json())
    .then(data => {
      Utils.hideLoading();
      
      if (data.error) {
        console.error("Error applying temporal filter:", data.error);
        alert(`Error applying temporal filter: ${data.error}`);
        return;
      }
      
      // Store date range from response for future reference
      if (data.date_range && Array.isArray(data.date_range) && data.date_range.length === 2) {
        this.temporalDateRange = data.date_range;
      }
      
      // Update the map with new tile layer
      MapManager.addOverlayLayer(data.tileUrl);
      
      // Add a visual confirmation message
      const confirmationMessage = document.createElement('div');
      confirmationMessage.className = 'visualization-confirmation';
      confirmationMessage.innerHTML = `
        <div class="notification success">
          Applied temporal filter: ${monthSelect.options[monthSelect.selectedIndex].text} ${year} 
          (median mosaic)
        </div>
      `;
      
      // Add to left panel and remove after a few seconds
      const leftPanel = document.getElementById('leftPanel');
      leftPanel.insertBefore(confirmationMessage, leftPanel.firstChild);
      
      // Remove after a few seconds
      setTimeout(() => {
        confirmationMessage.remove();
      }, 3000);
      
      console.log("Successfully applied temporal filter");
    })
    .catch(err => {
      Utils.hideLoading();
      console.error("Error applying temporal selection:", err);
      alert("Failed to apply temporal selection. See console for details.");
    });
  },
  
  /**
   * Create UI controls for band selection and colormap choice
   * @returns {string} HTML for band selection controls
   */
  createBandSelectionControls: function() {
    if (!this.availableBands || this.availableBands.length === 0) {
      return '';
    }
    
    // Find the currently selected band info
    const selectedBandInfo = this.availableBands.find(b => b.name === this.selectedBand) || this.availableBands[0];
    
    let html = `
      <div class="band-selection-controls">
        <h4>Band Visualization</h4>
        
        <div class="control-group">
          <label for="bandSelect">Select Band:</label>
          <select id="bandSelect" class="select-control">`;
    
    // Add options for each available band with descriptions and wavelength if available
    this.availableBands.forEach(band => {
      const selected = band.name === this.selectedBand ? 'selected' : '';
      
      // Format the option text with available metadata
      let optionText = band.name;
      
      if (band.description) {
        optionText += ` - ${band.description}`;
      }
      
      if (band.center_wavelength) {
        optionText += ` (${band.center_wavelength} μm)`;
      }
      
      html += `<option value="${band.name}" ${selected} data-min="${band.min}" data-max="${band.max}">${optionText}</option>`;
    });
    
    html += `
          </select>
        </div>
        
        <div class="control-group">
          <label for="colormapSelect">Select Colormap:</label>
          <select id="colormapSelect" class="select-control colormap-dropdown">`;
    
    // Add colormap options with styled gradient backgrounds using data-colors attribute
    this.availableColormaps.forEach(colormap => {
      const selected = colormap.id === this.selectedColormap ? 'selected' : '';
      html += `<option value="${colormap.id}" ${selected} data-colors="${colormap.colors.join(',')}">${colormap.name}</option>`;
    });
    
    html += `
          </select>
        </div>
        
        <div class="control-group range-control">
          <label>Adjust Range Values:</label>
          <div class="range-inputs">
            <div class="range-input">
              <label for="minValue">Min:</label>
              <input type="number" id="minValue" class="number-input" value="${selectedBandInfo.min || 0}">
            </div>
            <div class="range-input">
              <label for="maxValue">Max:</label>
              <input type="number" id="maxValue" class="number-input" value="${selectedBandInfo.max || 3000}">
            </div>
          </div>
        </div>
        
        <button id="applyBandBtn" class="action-button">Apply Visualization</button>
      </div>
    `;
    
    return html;
  },
  
  /**
   * Initialize band selection controls event listeners
   * @param {string} datasetId - Current dataset ID
   */
  initBandSelectionControls: function(datasetId) {
    // Band selection dropdown
    const bandSelect = document.getElementById('bandSelect');
    if (bandSelect) {
      bandSelect.addEventListener('change', () => {
        this.selectedBand = bandSelect.value;
        
        // Update min/max values based on the selected band
        const selectedOption = bandSelect.options[bandSelect.selectedIndex];
        const minValue = selectedOption.getAttribute('data-min') || 0;
        const maxValue = selectedOption.getAttribute('data-max') || 3000;
        
        // Update min/max input fields
        const minInput = document.getElementById('minValue');
        const maxInput = document.getElementById('maxValue');
        const minLabel = document.getElementById('minValueLabel');
        const maxLabel = document.getElementById('maxValueLabel');
        
        if (minInput) minInput.value = minValue;
        if (maxInput) maxInput.value = maxValue;
        if (minLabel) minLabel.textContent = minValue;
        if (maxLabel) maxLabel.textContent = maxValue;
        
        // Update the colormap preview
        this.updateColormapPreview();
      });
    }
    
    // Colormap selection dropdown
    const colormapSelect = document.getElementById('colormapSelect');
    if (colormapSelect) {
      // Apply colormap gradients to dropdown options
      this.applyColormapGradients(colormapSelect);
      
      colormapSelect.addEventListener('change', () => {
        this.selectedColormap = colormapSelect.value;
        this.updateColormapPreview();
      });
    }
    
    // Min/Max input fields
    const minInput = document.getElementById('minValue');
    const maxInput = document.getElementById('maxValue');
    const minLabel = document.getElementById('minValueLabel');
    const maxLabel = document.getElementById('maxValueLabel');
    
    if (minInput) {
      minInput.addEventListener('input', () => {
        if (minLabel) minLabel.textContent = minInput.value;
      });
    }
    
    if (maxInput) {
      maxInput.addEventListener('input', () => {
        if (maxLabel) maxLabel.textContent = maxInput.value;
      });
    }
    
    // Apply button
    const applyButton = document.getElementById('applyBandBtn');
    if (applyButton) {
      applyButton.addEventListener('click', () => {
        // Get current min/max values from inputs
        const currentMin = minInput ? parseFloat(minInput.value) : 0;
        const currentMax = maxInput ? parseFloat(maxInput.value) : 3000;
        
        this.applyBandVisualization(datasetId, currentMin, currentMax);
      });
    }
    
    // Initial colormap preview
    this.updateColormapPreview();
  },/**
  * Apply colormap gradients to dropdown options
  * @param {HTMLSelectElement} selectElement - The colormap dropdown element
  */
 applyColormapGradients: function(selectElement) {
   if (!selectElement) return;
   
   // Create a custom dropdown with styled options
   const wrapper = document.createElement('div');
   wrapper.className = 'colormap-wrapper';
   wrapper.style.position = 'relative';
   wrapper.style.display = 'inline-block';
   wrapper.style.width = '100%';
   
   // Replace the standard select with a styled div that shows the gradient
   const customSelect = document.createElement('div');
   customSelect.className = 'custom-colormap-select';
   customSelect.style.width = '100%';
   customSelect.style.height = '15px'; // 50% height reduction
   customSelect.style.border = '1px solid #ddd';
   customSelect.style.borderRadius = '4px';
   customSelect.style.cursor = 'pointer';
   customSelect.style.position = 'relative';
   
   // Selected option display area
   const selectedDisplay = document.createElement('div');
   selectedDisplay.className = 'selected-colormap';
   selectedDisplay.style.width = 'calc(100% - 20px)'; // Leave space for dropdown arrow
   selectedDisplay.style.height = '100%';
   selectedDisplay.style.display = 'flex';
   selectedDisplay.style.alignItems = 'center';
   
   // Add dropdown arrow
   const dropdownArrow = document.createElement('div');
   dropdownArrow.className = 'dropdown-arrow';
   dropdownArrow.style.position = 'absolute';
   dropdownArrow.style.right = '8px';
   dropdownArrow.style.top = '50%';
   dropdownArrow.style.transform = 'translateY(-50%)';
   dropdownArrow.style.width = '0';
   dropdownArrow.style.height = '0';
   dropdownArrow.style.borderLeft = '5px solid transparent';
   dropdownArrow.style.borderRight = '5px solid transparent';
   dropdownArrow.style.borderTop = '5px solid #555';
   
   // Add range labels directly below the selected colormap
   const rangeLabels = document.createElement('div');
   rangeLabels.className = 'range-labels';
   rangeLabels.style.display = 'flex';
   rangeLabels.style.justifyContent = 'space-between';
   rangeLabels.style.fontSize = '12px';
   rangeLabels.style.marginTop = '2px';
   rangeLabels.style.color = '#666';
   
   // Min/max labels
   const minLabel = document.createElement('span');
   minLabel.id = 'minValueLabel';
   minLabel.textContent = document.getElementById('minValue')?.value || '0';
   
   const maxLabel = document.createElement('span');
   maxLabel.id = 'maxValueLabel';
   maxLabel.textContent = document.getElementById('maxValue')?.value || '3000';
   
   rangeLabels.appendChild(minLabel);
   rangeLabels.appendChild(maxLabel);
   
   // Create dropdown options container
   const optionsContainer = document.createElement('div');
   optionsContainer.className = 'colormap-options';
   optionsContainer.style.position = 'absolute';
   optionsContainer.style.width = '100%';
   optionsContainer.style.backgroundColor = '#fff';
   optionsContainer.style.border = '1px solid #ddd';
   optionsContainer.style.borderRadius = '4px';
   optionsContainer.style.marginTop = '2px';
   optionsContainer.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
   optionsContainer.style.zIndex = '100';
   optionsContainer.style.maxHeight = '150px';
   optionsContainer.style.overflowY = 'auto';
   optionsContainer.style.display = 'none';
   
   // Process all options
   Array.from(selectElement.options).forEach(option => {
     const colorsAttr = option.getAttribute('data-colors');
     const colors = colorsAttr ? colorsAttr.split(',') : [];
     const gradient = colors.length > 0 ? 
       `linear-gradient(to right, ${colors.join(', ')})` : '#f0f0f0';
     
     // Create a div for each option
     const optionDiv = document.createElement('div');
     optionDiv.className = 'colormap-option';
     optionDiv.dataset.value = option.value;
     optionDiv.style.height = '15px'; // 50% height reduction
     optionDiv.style.padding = '0'; // Remove padding
     optionDiv.style.cursor = 'pointer';
     optionDiv.style.background = gradient;
     optionDiv.style.borderBottom = '1px solid #eee';
     
     // Add hover effect
     optionDiv.addEventListener('mouseover', () => {
       optionDiv.style.opacity = '0.9';
     });
     
     optionDiv.addEventListener('mouseout', () => {
       optionDiv.style.opacity = '1';
     });
     
     // Set click handler
     optionDiv.addEventListener('click', () => {
       selectElement.value = option.value;
       // Trigger change event
       selectElement.dispatchEvent(new Event('change'));
       
       // Update custom select display
       selectedDisplay.style.background = gradient;
       
       // Hide options
       optionsContainer.style.display = 'none';
     });
     
     optionsContainer.appendChild(optionDiv);
     
     // If this is the selected option, update the display
     if (option.selected) {
       selectedDisplay.style.background = gradient;
     }
   });
   
   // Toggle dropdown on click
   customSelect.addEventListener('click', (e) => {
     e.stopPropagation();
     const isVisible = optionsContainer.style.display === 'block';
     optionsContainer.style.display = isVisible ? 'none' : 'block';
   });
   
   // Hide dropdown when clicking outside
   document.addEventListener('click', () => {
     optionsContainer.style.display = 'none';
   });
   
   // Add elements to the DOM
   customSelect.appendChild(selectedDisplay);
   customSelect.appendChild(dropdownArrow);
   wrapper.appendChild(customSelect);
   wrapper.appendChild(rangeLabels);
   wrapper.appendChild(optionsContainer);
   
   // Replace the select with our custom implementation
   selectElement.style.display = 'none';
   selectElement.parentNode.insertBefore(wrapper, selectElement.nextSibling);
   
   // Remove the old colormap preview as we're now showing min/max directly under the colorbar
   const oldPreview = document.getElementById('colormapPreview');
   if (oldPreview) {
     const previewContainer = oldPreview.parentElement;
     if (previewContainer && previewContainer.className === 'preview-container') {
       previewContainer.style.display = 'none';
     }
   }
 },
 
 /**
  * Update the colormap preview based on selected colormap
  */
 updateColormapPreview: function() {
   // Get min/max values
   const minValue = document.getElementById('minValue');
   const maxValue = document.getElementById('maxValue');
   
   // Update labels
   const minLabel = document.getElementById('minValueLabel');
   const maxLabel = document.getElementById('maxValueLabel');
   
   if (minLabel && minValue) minLabel.textContent = minValue.value;
   if (maxLabel && maxValue) maxLabel.textContent = maxValue.value;
 },
 
 /**
  * Apply the selected band and colormap visualization
  * @param {string} datasetId - Current dataset ID
  * @param {number} minValue - Minimum value for visualization
  * @param {number} maxValue - Maximum value for visualization
  */
 applyBandVisualization: function(datasetId, minValue, maxValue) {
   // Show loading indicator
   Utils.showLoading();
   
   // Find information for the selected band
   const bandInfo = this.availableBands.find(b => b.name === this.selectedBand);
   if (!bandInfo) {
     Utils.hideLoading();
     console.error("Selected band information not found");
     return;
   }
   
   // Find the selected colormap
   const colormap = this.availableColormaps.find(cm => cm.id === this.selectedColormap);
   if (!colormap) {
     Utils.hideLoading();
     console.error("Selected colormap not found");
     return;
   }
   
   // Log detailed band information
   console.log("Applying visualization for band:", bandInfo);
   console.log(`Using custom min/max values: min=${minValue}, max=${maxValue}`);
   
   // Create visualization parameters
   const visParams = {
     band: this.selectedBand,
     colormap: this.selectedColormap,
     colormap_colors: colormap.colors,
     min: minValue !== undefined ? minValue : bandInfo.min || 0,
     max: maxValue !== undefined ? maxValue : bandInfo.max || 3000
   };
   
   // Add temporal filter if this is a temporal dataset
   if (this.temporalSelection.isTemporalDataset) {
     const year = this.temporalSelection.year;
     const month = this.temporalSelection.month;
     
     // Format month with leading zero if needed
     const monthFormatted = month < 10 ? `0${month}` : `${month}`;
     
     // Create date range for the selected month
     const startDate = `${year}-${monthFormatted}-01`;
     const lastDay = new Date(year, month, 0).getDate();
     const endDate = `${year}-${monthFormatted}-${lastDay}`;
     
     visParams.temporal_filter = {
       start_date: startDate,
       end_date: endDate,
       aggregation: 'median'  // Compute median mosaic
     };
     
     console.log("Including temporal filter:", visParams.temporal_filter);
   }
   
   console.log("Sending visualization parameters to server:", visParams);
   
   // Make request to update visualization
   fetch('/get_tile', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({ 
       dataset_id: datasetId,
       visualization: visParams
     })
   })
   .then(response => response.json())
   .then(data => {
     Utils.hideLoading();
     
     if (data.error) {
       console.error("Error applying band visualization:", data.error);
       alert("Error applying visualization: " + data.error);
       return;
     }
     
     console.log("Visualization response from server:", data);
     
     // Update the map with new tile layer
     MapManager.addOverlayLayer(data.tileUrl);
     
     // Update palette display if available
     if (data.palette) {
       const paletteContainer = document.querySelector('.palette-container');
       if (paletteContainer) {
         paletteContainer.innerHTML = '';
         paletteContainer.insertAdjacentHTML('beforeend', 
           Utils.createPaletteDisplay(data.palette, data.min, data.max));
       }
     }
     
     // Add a visual confirmation message
     const confirmationMessage = document.createElement('div');
     confirmationMessage.className = 'visualization-confirmation';
     confirmationMessage.innerHTML = `
       <div class="notification success">
         Applied visualization for band <strong>${bandInfo.name}</strong> 
         with <strong>${colormap.name}</strong> colormap (range: ${visParams.min} to ${visParams.max})
       </div>
     `;
     
     // Add to left panel and remove after a few seconds
     const leftPanel = document.getElementById('leftPanel');
     leftPanel.insertBefore(confirmationMessage, leftPanel.firstChild);
     
     setTimeout(() => {
       confirmationMessage.remove();
     }, 3000);
     
     console.log("Successfully applied new band visualization:", visParams);
   })
   .catch(err => {
     Utils.hideLoading();
     console.error("Error applying band visualization:", err);
     alert("Failed to apply visualization. See console for details.");
   });
 },
 
 /**
  * Create feature collection style controls
  * @returns {string} - HTML for the styling controls
  */
 createFeatureStyleControls: function() {
   // Create style control options
   const html = `
     <div class="feature-style-controls">
       <h4>Feature Style</h4>
       <div class="style-options">
         <button class="style-btn active" data-style="default">
           <div class="style-preview default-style"></div>
           <span>Default</span>
         </button>
         <button class="style-btn" data-style="blue">
           <div class="style-preview blue-style"></div>
           <span>Blue</span>
         </button>
         <button class="style-btn" data-style="outline">
           <div class="style-preview outline-style"></div>
           <span>Outline</span>
         </button>
         <button class="style-btn" data-style="random">
           <div class="style-preview random-style"></div>
           <span>Random</span>
         </button>
       </div>
     </div>
   `;
   
   return html;
 },
 
 /**
  * Initialize feature style controls
  * @param {string} datasetId - The dataset ID
  */
 initFeatureStyleControls: function(datasetId) {
   // Add event listeners to style buttons
   document.querySelectorAll('.style-btn').forEach(button => {
     button.addEventListener('click', () => {
       // Remove active class from all buttons
       document.querySelectorAll('.style-btn').forEach(btn => {
         btn.classList.remove('active');
       });
       
       // Add active class to clicked button
       button.classList.add('active');
       
       // Apply the selected style
       const styleType = button.getAttribute('data-style');
       this.applyFeatureStyle(styleType, datasetId);
     });
   });
 },
 
 /**
  * Apply a feature style based on the selected option
  * @param {string} styleType - The style type ('default', 'blue', etc.)
  * @param {string} datasetId - The dataset ID
  */
 applyFeatureStyle: function(styleType, datasetId) {
   // Define style parameters based on the selected style
   let styleParams = {};
   
   switch (styleType) {
     case 'blue':
       styleParams = {
         fillColor: '#4285F455',  // Semi-transparent blue fill
         color: '#4285F4',        // Google blue border
         width: 1.5,              // Slightly thicker border
         style_type: 'default'
       };
       break;
     case 'outline':
       styleParams = {
         color: '#0066cc',      // Blue border
         width: 2.0,            // Thicker lines
         style_type: 'outline_only'
       };
       break;
     case 'random':
       styleParams = {
         style_type: 'random_colors'  // Server will assign random colors
       };
       break;
     default:
       styleParams = {
         fillColor: '#34A85355',  // Semi-transparent green fill
         color: '#34A853',        // Google green border
         width: 1.0,              // Standard width
         style_type: 'default'
       };
   }
   
   // Show loading indicator
   Utils.showLoading();
   
   // Make API request with style parameters
   fetch('/get_tile', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({ 
       dataset_id: datasetId,
       style: styleParams
     })
   })
   .then(response => response.json())
   .then(data => {
     Utils.hideLoading();
     
     if (data.error) {
       console.error("Error applying style:", data.error);
       return;
     }
     
     // Add the new tile layer to replace the current one
     MapManager.addOverlayLayer(data.tileUrl);
   })
   .catch(err => {
     Utils.hideLoading();
     console.error("Error applying feature style:", err);
   });
 }


 
};