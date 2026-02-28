/**
 * UI components and interaction handling
 */
const UI = {
  /**
   * Initialize UI components and event listeners
   */
  init: function() {
    // Initialize modals
    this.initModals();
    
    console.log("UI initialized");
  },

  /**
   * Initialize modal functionality
   */
  initModals: function() {
    // About modal
    const aboutButton = document.getElementById('aboutButton');
    const aboutModal = document.getElementById('aboutModal');
    
    if (aboutButton && aboutModal) {
      const aboutClose = aboutModal.querySelector('.close-modal');
      
      aboutButton.addEventListener('click', function(e) {
        e.preventDefault();
        aboutModal.style.display = 'block';
      });
      
      if (aboutClose) {
        aboutClose.addEventListener('click', function() {
          aboutModal.style.display = 'none';
        });
      }
      
      // Close when clicking outside
      window.addEventListener('click', function(event) {
        if (event.target === aboutModal) {
          aboutModal.style.display = 'none';
        }
      });
    }
    
    // Help button - link to wiki help modal
    const helpButton = document.getElementById('helpButton');
    const wikiHelpModal = document.getElementById('wikiHelpModal');
    
    if (helpButton && wikiHelpModal) {
      const wikiClose = wikiHelpModal.querySelector('.close-modal');
      const closeWikiHelp = document.getElementById('closeWikiHelp');
      
      helpButton.addEventListener('click', function(e) {
        e.preventDefault();
        wikiHelpModal.style.display = 'block';
      });
      
      if (wikiClose) {
        wikiClose.addEventListener('click', function() {
          wikiHelpModal.style.display = 'none';
        });
      }
      
      if (closeWikiHelp) {
        closeWikiHelp.addEventListener('click', function() {
          wikiHelpModal.style.display = 'none';
        });
      }
      
      // Close when clicking outside
      window.addEventListener('click', function(event) {
        if (event.target === wikiHelpModal) {
          wikiHelpModal.style.display = 'none';
        }
      });
    }
  },

  /**
   * Update debug information in the console only
   */
  updateDebugInfo: function() {
    // Only log to console, no UI updates needed
    // MapManager.logMapDebugInfo() now handles this
  }
};