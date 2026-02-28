/**
 * Dataset search functionality
 */
const Search = {
  // Store search results for reference
  searchResults: [],
  
  /**
   * Submit the search query and display results
   * @param {string} query - Search query string
   */
  searchDatasets: function(query) {
    if (!query.trim()) {
      alert('Please enter a search query');
      return;
    }
    
    Utils.showLoading();
    
    fetch('/search_datasets', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
      Utils.hideLoading();
      // Store search results
      this.searchResults = data.results || [];
      this.displaySearchResults(data);
    })
    .catch(err => {
      Utils.hideLoading();
      console.error("Error:", err);
      document.getElementById('resultsPanel').innerHTML = "<p>Error fetching datasets. Please try again.</p>";
    });
  },
  
  /**
   * Display search results in the results panel
   * @param {Object} data - Search results data
   */
  displaySearchResults: function(data) {
    var panel = document.getElementById('resultsPanel');
    panel.innerHTML = "";
    
    // Show the results panel when search is performed
    panel.style.display = "block";
    
    if (data.results && data.results.length > 0) {
      data.results.forEach(function(item) {
        var div = document.createElement('div');
        div.className = "result-item";
        div.dataset.id = item.id;  // Store dataset ID in the DOM element
        
        // When a result item is clicked, pass both the ID and the dataset info
        div.onclick = function() { 
          // Find the dataset in our stored results
          const datasetInfo = Search.searchResults.find(result => result.id === item.id);
          DatasetManager.loadDataset(item.id, false, datasetInfo); 
        };
        
        // Get the dataset type and create a badge
        var datasetType = item['gee:type'] || 'image_collection';
        var typeBadge = '';
        
        if (datasetType.toLowerCase() === 'image') {
          typeBadge = '<span class="dataset-type-badge type-image">Image</span>';
        } else if (datasetType.toLowerCase() === 'table') {
          typeBadge = '<span class="dataset-type-badge type-table">Feature Collection</span>';
        } else {
          typeBadge = '<span class="dataset-type-badge type-collection">Image Collection</span>';
        }
        
        // Title and description
        var content = "<h4>" + item.title + typeBadge + "</h4>" +
                     "<p>" + item.description.substring(0, 150) + "...</p>";
        
        // Add preview image if available
        if (item.preview_url) {
          content += "<img src='" + item.preview_url + "' alt='Preview' onerror=\"this.style.display='none'\" />";
        }
        
        div.innerHTML = content;
        panel.appendChild(div);
      });
    } else {
      panel.innerHTML = "<p>No datasets found matching your query.</p>";
    }
  },
  
  /**
   * Initialize search-related event listeners
   */
  initEventListeners: function() {
    // Button click event
    document.getElementById('searchButton').addEventListener('click', () => {
      const query = document.getElementById('queryInput').value;
      this.searchDatasets(query);
    });
    
    // Keyboard shortcut for search (Enter key)
    document.getElementById('queryInput').addEventListener('keyup', (event) => {
      if (event.key === 'Enter') {
        const query = document.getElementById('queryInput').value;
        this.searchDatasets(query);
      }
    });
  }
};
