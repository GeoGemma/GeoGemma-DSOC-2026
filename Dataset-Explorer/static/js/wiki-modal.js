/**
 * Wiki Help functionality for dataset descriptions
 */
const WikiHelp = {
  // Track whether the modal has been shown before
  modalShownBefore: false,
  
  /**
   * Initialize the Wiki Help system
   */
  init: function() {
    // Add event listeners for the modal
    this.setupEventListeners();
    
    // Add help trigger button to dataset description section
    this.addHelpTrigger();
  },
  
  /**
   * Set up event listeners for the modal
   */
  setupEventListeners: function() {
    // Get the modal elements
    const modal = document.getElementById('wikiHelpModal');
    const closeBtn = document.querySelector('.close-modal');
    const closeButton = document.getElementById('closeWikiHelp');
    
    // Close button click
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        modal.style.display = "none";
      });
    }
    
    // "Got it" button click
    if (closeButton) {
      closeButton.addEventListener('click', function() {
        modal.style.display = "none";
      });
    }
    
    // Click outside modal to close
    window.addEventListener('click', function(event) {
      if (event.target === modal) {
        modal.style.display = "none";
      }
    });
  },
  
  /**
   * Add a help trigger button to the dataset description
   */
  addHelpTrigger: function() {
    // This gets called when the left panel is updated
    // Monitor for when the dataset description is added to the DOM
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          // Check if the dataset description is in the DOM
          const descDiv = document.querySelector('.dataset-description');
          if (descDiv && !descDiv.querySelector('.wiki-help-trigger')) {
            // Add the help trigger button
            const helpTrigger = document.createElement('div');
            helpTrigger.className = 'wiki-help-trigger';
            helpTrigger.textContent = '?';
            helpTrigger.title = 'Learn about Wikipedia links';
            helpTrigger.addEventListener('click', () => this.showHelpModal());
            
            // Add it to the description div
            descDiv.style.position = 'relative';
            descDiv.appendChild(helpTrigger);
            
            // REMOVED: Auto-show the help modal
            // The automatic modal display has been removed
          }
        }
      });
    });
    
    // Start observing the left panel for changes
    observer.observe(document.getElementById('leftPanel'), { childList: true, subtree: true });
  },
  
  /**
   * Show the help modal
   */
  showHelpModal: function() {
    const modal = document.getElementById('wikiHelpModal');
    if (modal) {
      modal.style.display = "block";
    }
  }
};

// Initialize the Wiki Help when the document is ready
document.addEventListener('DOMContentLoaded', function() {
  WikiHelp.init();
});