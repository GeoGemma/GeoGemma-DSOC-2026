// src/components/Sidebar/RightSidebar.jsx
import { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  ChevronLeft, 
  ChevronRight, 
  Layers, 
  Crosshair, 
  Info, 
  Trash2, 
  Maximize,
  Link,
  ArrowUpDown
} from 'lucide-react';
import { useMap } from '../../contexts/MapContext';
import MapInspector from '../Map/MapInspector';
import MapLegend from '../Map/MapLegend';
import LayersList from './LayersList';
import { clearLayers as clearLayersApi } from '../../services/api';
import '../../styles/RightSidebar.css';
import '../../styles/layerList.css';

const RightSidebar = ({ showNotification }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeSection, setActiveSection] = useState('layers'); // Default to layers
  const [selectedLayerId, setSelectedLayerId] = useState(null);
  const { layers, clearLayers } = useMap();

  // Find the selected layer object based on selectedLayerId
  const selectedLayer = layers.find(layer => layer.id === selectedLayerId);

  const toggleSidebar = () => {
    setIsExpanded(!isExpanded);
  };

  const toggleSection = (section) => {
    setActiveSection(activeSection === section ? null : section);
    
    // Auto-expand sidebar when section is selected
    if (!isExpanded && section) {
      setIsExpanded(true);
    }
  };

  const handleLayerSelect = (layerId) => {
    setSelectedLayerId(layerId);
    // Don't automatically switch tabs - we want to stay on the layers tab
    // while centering the map on the selected layer
  };

  const handleClearLayers = async () => {
    try {
      await clearLayers(); // This will clear both map and Firestore layers for the user
      setSelectedLayerId(null); // Clear selection when all layers are removed
      showNotification('All layers cleared successfully', 'success');
    } catch (error) {
      showNotification('Error clearing layers', 'error');
    }
  };

  const handleFullscreen = () => {
    const element = document.documentElement;
    if (!document.fullscreenElement) {
      if (element.requestFullscreen) {
        element.requestFullscreen();
      } else if (element.webkitRequestFullscreen) { /* Safari */
        element.webkitRequestFullscreen();
      } else if (element.msRequestFullscreen) { /* IE11 */
        element.msRequestFullscreen();
      }
      showNotification('Entered fullscreen mode', 'info');
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) { /* Safari */
        document.webkitExitFullscreen();
      } else if (document.msExitFullscreen) { /* IE11 */
        document.msExitFullscreen();
      }
      showNotification('Exited fullscreen mode', 'info');
    }
  };

  const handleShare = () => {
    // Share functionality
    showNotification('Sharing feature coming soon', 'info');
  };

  // Function to sort layers by different criteria
  const handleSortLayers = () => {
    // This could be expanded to show a dropdown with different sort options
    showNotification('Layer sorting options coming soon', 'info');
  };

  return (
    <div className={`right-sidebar ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {/* Toggle Button */}
      <div className="sidebar-toggle-container">
        <button 
          onClick={toggleSidebar}
          className="sidebar-toggle-btn"
          title={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
          aria-label={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
        >
          {isExpanded ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
      
      {/* Sidebar Content - Only rendered when expanded */}
      {isExpanded ? (
        <div className="right-sidebar-content">
          {/* Sidebar Header */}
          <div className="sidebar-header">
            <h2 className="sidebar-title">Map Controls</h2>
          </div>

          {/* Tool Tabs */}
          <div className="sidebar-tabs">
            <button 
              className={`sidebar-tab ${activeSection === 'layers' ? 'active' : ''}`}
              onClick={() => toggleSection('layers')}
            >
              Layers
            </button>
            <button 
              className={`sidebar-tab ${activeSection === 'inspect' ? 'active' : ''}`}
              onClick={() => toggleSection('inspect')}
            >
              Inspect
            </button>
            <button 
              className={`sidebar-tab ${activeSection === 'info' ? 'active' : ''}`}
              onClick={() => toggleSection('info')}
            >
              Info
            </button>
          </div>

          {/* Content Area */}
          <div className="sidebar-content-area">
            {/* Layers Panel */}
            {activeSection === 'layers' && (
              <div className="content-panel">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-google-grey-100 text-sm font-medium flex items-center gap-1">
                    <Layers size={16} /> 
                    <span>Map Layers</span>
                    {layers.length > 0 && <span className="bg-google-bg-light text-xs px-2 py-0.5 rounded-full">{layers.length}</span>}
                  </h3>
                  {layers.length > 0 && (
                    <div className="flex gap-2">
                      <button 
                        className="text-xs flex items-center gap-1 py-1 px-2 rounded border border-google-grey-300/20 text-google-grey-200 hover:bg-google-bg-lighter"
                        title="Sort layers"
                        onClick={handleSortLayers}
                      >
                        <ArrowUpDown size={14} />
                        <span>Sort</span>
                      </button>
                    </div>
                  )}
                </div>
                
                {layers.length > 0 ? (
                  <>
                    {/* Pass onLayerSelect and selectedLayerId props to LayersList */}
                    <LayersList 
                      showNotification={showNotification} 
                      onLayerSelect={handleLayerSelect}
                      selectedLayerId={selectedLayerId}
                    />
                    
                    {/* Clear Layers Button */}
                    <div className="mt-4">
                      <button 
                        className="w-full py-2 px-4 rounded-md bg-google-red/10 text-google-red hover:bg-google-red/20 transition-colors font-medium text-sm flex items-center justify-center gap-2"
                        onClick={handleClearLayers}
                      >
                        <Trash2 size={16} />
                        Clear All Layers
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="bg-google-bg-light rounded-lg p-6 text-center">
                    <div className="text-google-grey-100 mb-2">No layers available</div>
                    <p className="text-google-grey-300 text-sm">Enter a query in the search bar to add a layer to the map.</p>
                  </div>
                )}
              </div>
            )}
            
            {/* Inspect Panel */}
            {activeSection === 'inspect' && (
              <div className="content-panel">
                <MapInspector showNotification={showNotification} />
              </div>
            )}
            
            {/* Info Panel - Pass the selectedLayer to MapLegend if available */}
            {activeSection === 'info' && (
              <div className="content-panel">
                <MapLegend selectedLayer={selectedLayer} />
              </div>
            )}
          </div>
        </div>
      ) : (
        // Collapsed sidebar with icons
        <div className="sidebar-collapsed-content">
          <div className="sidebar-icon-group">
            <button 
              className={`sidebar-icon-btn ${activeSection === 'layers' ? 'active' : ''}`}
              onClick={() => toggleSection('layers')}
              title="Layers"
            >
              <Layers size={20} />
            </button>
            
            <button 
              className={`sidebar-icon-btn ${activeSection === 'inspect' ? 'active' : ''}`}
              onClick={() => toggleSection('inspect')}
              title="Inspect"
            >
              <Crosshair size={20} />
            </button>
            
            <button 
              className={`sidebar-icon-btn ${activeSection === 'info' ? 'active' : ''}`}
              onClick={() => toggleSection('info')}
              title="Information"
            >
              <Info size={20} />
            </button>
            
            <button 
              className="sidebar-icon-btn"
              onClick={handleFullscreen}
              title="Fullscreen"
            >
              <Maximize size={20} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

RightSidebar.propTypes = {
  showNotification: PropTypes.func.isRequired
};

export default RightSidebar;