/**
 * Prompt bar functionality for searching suggestions
 */
document.addEventListener('DOMContentLoaded', function() {
    initPromptBar();
  });
  
  function initPromptBar() {
    const promptBar = document.querySelector('.modern-prompt-bar');
    const collapseBtn = document.querySelector('.prompt-collapse-btn');
    const expandBtn = document.querySelector('.prompt-expand-btn');
    const promptExamples = document.querySelectorAll('.prompt-example');
    const searchButton = document.getElementById('searchButton');
    const queryInput = document.getElementById('queryInput');
    
    // Initially show the prompt bar
    promptBar.classList.remove('hidden');
    
    // Handle collapse button click
    if (collapseBtn) {
      collapseBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        promptBar.classList.add('collapsed');
      });
    }
    
    // Handle expand button click
    if (expandBtn) {
      expandBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        promptBar.classList.remove('collapsed');
        promptBar.classList.remove('hidden');
      });
    }
    
    // Handle clicks on prompt examples
    promptExamples.forEach(example => {
      example.addEventListener('click', function() {
        const query = this.getAttribute('data-query');
        queryInput.value = query;
        queryInput.focus();
        
        // Add animation effect
        this.style.backgroundColor = '#e8f0fe';
        setTimeout(() => {
          this.style.backgroundColor = '';
        }, 300);
        
        // Optional: automatically trigger search after selecting an example
        // searchButton.click();
      });
    });
    
    // Hide prompt bar when search is executed
    if (searchButton) {
      searchButton.addEventListener('click', function() {
        if (queryInput.value.trim() !== '') {
          promptBar.classList.add('hidden');
        }
      });
    }
    
    // Also hide when pressing Enter in the input
    queryInput.addEventListener('keyup', function(event) {
      if (event.key === 'Enter' && queryInput.value.trim() !== '') {
        promptBar.classList.add('hidden');
      }
    });
    
    // Show the prompt bar when clicking on an empty input or the expand button
    queryInput.addEventListener('click', function() {
      if (queryInput.value.trim() === '') {
        promptBar.classList.remove('hidden');
        promptBar.classList.remove('collapsed');
      }
    });
    
    // Add keyboard navigation for accessibility
    promptBar.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        promptBar.classList.add('collapsed');
        queryInput.focus();
      }
    });
    
    // Make examples tabbable for accessibility
    promptExamples.forEach(example => {
      example.setAttribute('tabindex', '0');
      example.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          example.click();
        }
      });
    });
    
    // Close the prompt bar when clicking outside
    document.addEventListener('click', function(e) {
      if (!promptBar.contains(e.target) && 
          !expandBtn.contains(e.target) && 
          !queryInput.contains(e.target)) {
        promptBar.classList.add('collapsed');
      }
    });
  
    // Fix for the up/down arrow in the prompt-collapse-btn
    const arrowToggle = document.querySelector('.prompt-collapse-btn svg');
    if (arrowToggle) {
      collapseBtn.addEventListener('click', function() {
        // Toggle the arrow direction
        if (promptBar.classList.contains('collapsed')) {
          arrowToggle.innerHTML = '<polyline points="6 9 12 15 18 9"></polyline>';
        } else {
          arrowToggle.innerHTML = '<polyline points="18 15 12 9 6 15"></polyline>';
        }
      });
    }
    
    // Fix for search icon button in the search bar
    const searchIcon = document.querySelector('.prompt-expand-btn svg');
    if (searchIcon) {
      expandBtn.addEventListener('click', function() {
        // Toggle the display state of the prompt bar
        if (promptBar.classList.contains('hidden') || promptBar.classList.contains('collapsed')) {
          promptBar.classList.remove('hidden');
          promptBar.classList.remove('collapsed');
          searchIcon.innerHTML = '<polyline points="18 15 12 9 6 15"></polyline>';
        } else {
          promptBar.classList.add('collapsed');
          searchIcon.innerHTML = '<polyline points="6 9 12 15 18 9"></polyline>';
        }
      });
    }
  }