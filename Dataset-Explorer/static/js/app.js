/**
 * Main application initialization
 */
document.addEventListener('DOMContentLoaded', function() {
  // Initialize map
  MapManager.init();
  
  // Initialize UI components
  UI.init();
  
  // Initialize search functionality
  Search.initEventListeners();
  
  // Initialize prompt bar functionality
  initPromptBar();
  
  console.log('GEE Dataset Explorer initialized');
});