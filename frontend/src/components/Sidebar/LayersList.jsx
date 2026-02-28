// src/components/Sidebar/LayersList.jsx
import { useState, useRef } from 'react';
import PropTypes from 'prop-types';
import { Eye, EyeOff, Trash2, ChevronDown, ChevronUp, GripVertical, Info } from 'lucide-react';
import { useMap } from '../../contexts/MapContext';
import { deleteLayer as deleteLayerApi } from '../../services/api';

const LayersList = ({ showNotification, onLayerSelect, selectedLayerId }) => {
  const { layers, toggleLayerVisibility, removeLayer, setLayerOpacity, reorderLayers, focusOnLayer } = useMap();
  const [expandedLayers, setExpandedLayers] = useState({});
  const [draggedItem, setDraggedItem] = useState(null);
  const dragOverItemRef = useRef(null);

  const handleToggleVisibility = (e, layerId) => {
    e.stopPropagation();
    toggleLayerVisibility(layerId);
  };

  const handleDeleteLayer = async (e, layerId) => {
    e.stopPropagation();
    try {
      await deleteLayerApi(layerId);
      removeLayer(layerId);
      showNotification('Layer removed', 'success');
      
      // If the deleted layer was selected, clear the selection
      if (selectedLayerId === layerId && onLayerSelect) {
        onLayerSelect(null);
      }
    } catch (error) {
      showNotification('Error removing layer', 'error');
    }
  };

  const handleOpacityChange = (e, layerId, opacity) => {
    // Stop event propagation to prevent layer selection when adjusting opacity
    e.stopPropagation();
    setLayerOpacity(layerId, opacity);
  };

  const toggleLayerExpanded = (e, layerId) => {
    e.stopPropagation();
    setExpandedLayers(prev => ({
      ...prev,
      [layerId]: !prev[layerId]
    }));
  };

  // Layer selection handler that focuses the map on the layer output
  const handleLayerClick = (layer) => {
    // Select the layer
    if (onLayerSelect) {
      onLayerSelect(layer.id);
    }
    
    // Focus on the layer's output area instead of just center coordinates
    focusOnLayer(layer.id);
    
    // Show notification
    showNotification(`Viewing ${layer.processing_type} layer for ${layer.location}`, 'info');
  };

  // Drag and drop handlers
  const handleDragStart = (e, index) => {
    // Set data to satisfy Firefox's implementation
    e.dataTransfer.setData('text/plain', index.toString());
    setDraggedItem(index);
    e.dataTransfer.effectAllowed = "move";
    // Make the drag element transparent
    e.target.style.opacity = 0.5;
  };

  const handleDragEnd = (e) => {
    e.target.style.opacity = 1;
    setDraggedItem(null);
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    dragOverItemRef.current = index;
    
    // Add visual indicator for drop position
    const items = document.querySelectorAll('.layer-item');
    items.forEach(item => item.classList.remove('drop-target'));
    
    if (items[index]) {
      items[index].classList.add('drop-target');
    }
  };

  const handleDragLeave = (e) => {
    // Remove visual indicator
    const items = document.querySelectorAll('.layer-item');
    items.forEach(item => item.classList.remove('drop-target'));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    
    // Remove visual indicator
    const items = document.querySelectorAll('.layer-item');
    items.forEach(item => item.classList.remove('drop-target'));
    
    if (draggedItem !== null && dragOverItemRef.current !== null) {
      if (draggedItem !== dragOverItemRef.current) {
        // Copy the layers array
        const newLayers = [...layers];
        
        // Remove dragged item
        const draggedLayer = newLayers.splice(draggedItem, 1)[0];
        
        // Insert at new position
        newLayers.splice(dragOverItemRef.current, 0, draggedLayer);
        
        // Update layers via context - this will now properly reorder the visual stack
        reorderLayers(newLayers);
        
        showNotification('Layer order updated', 'success');
      }
    }
    
    // Reset references
    setDraggedItem(null);
    dragOverItemRef.current = null;
  };

  // Color indicators for different layer types
  const getLayerTypeColor = (type) => {
    const typeColors = {
      'RGB': 'bg-google-blue',
      'NDVI': 'bg-google-green',
      'SURFACE WATER': 'bg-blue-500',
      'LULC': 'bg-google-yellow',
      'LST': 'bg-google-red',
      'OPEN BUILDINGS': 'bg-purple-500'
    };
    
    return typeColors[type] || 'bg-google-grey-300';
  };

  if (layers.length === 0) {
    return (
      <div className="text-center py-6 px-4">
        <p className="text-google-grey-300 text-sm">No layers available</p>
        <p className="text-google-grey-400 text-xs mt-1">Enter a query to add a layer</p>
      </div>
    );
  }

  return (
    <ul className="list-none p-2 space-y-2">
      {layers.map((layer, index) => {
        const isVisible = layer.visibility !== 'none';
        const isExpanded = expandedLayers[layer.id];
        const isSelected = layer.id === selectedLayerId;
        
        return (
          <li 
            key={layer.id} 
            className={`layer-item bg-background-surface rounded-lg hover:bg-background-surface/80 transition-colors 
                     border border-background-light/30 cursor-pointer ${isSelected ? 'ring-1 ring-google-blue bg-google-bg-lighter' : ''}`}
            draggable
            onDragStart={(e) => handleDragStart(e, index)}
            onDragEnd={handleDragEnd}
            onDragOver={(e) => handleDragOver(e, index)}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => handleLayerClick(layer)}
          >
            <div className="p-2">
              {/* Layer header with controls */}
              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <div className="drag-handle p-1 cursor-grab mr-1 text-google-grey-300 hover:text-google-grey-100">
                    <GripVertical size={14} />
                  </div>
                  <div className={`w-3 h-3 rounded-full mr-2 ${getLayerTypeColor(layer.processing_type)}`}></div>
                  <span className="text-sm text-google-grey-100 font-medium truncate max-w-[120px]">
                    {layer.location}
                  </span>
                </div>
                <div className="flex space-x-1">
                  <button 
                    className="p-1 rounded-full text-google-grey-300 hover:text-google-grey-100 hover:bg-background-light/50"
                    onClick={(e) => handleToggleVisibility(e, layer.id)}
                    title={isVisible ? "Hide layer" : "Show layer"}
                  >
                    {isVisible ? <Eye size={16} /> : <EyeOff size={16} />}
                  </button>
                  <button 
                    className="p-1 rounded-full text-google-grey-300 hover:text-google-red hover:bg-background-light/50" 
                    onClick={(e) => handleDeleteLayer(e, layer.id)}
                    title="Remove layer"
                  >
                    <Trash2 size={16} />
                  </button>
                  <button
                    className="p-1 rounded-full text-google-grey-300 hover:text-google-grey-100 hover:bg-background-light/50"
                    onClick={(e) => toggleLayerExpanded(e, layer.id)}
                    title={isExpanded ? "Collapse" : "Expand"}
                  >
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>
              </div>
              
              {/* Layer type indicator */}
              <div className="mt-1 text-xs text-google-grey-300">
                {layer.processing_type}
              </div>
              
              {/* Expanded details */}
              {isExpanded && isVisible && (
                <div className="mt-3 pt-2 border-t border-background-light/30">
                  {/* Opacity slider */}
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-google-grey-300 w-14">Opacity:</label>
                    <input 
                      type="range" 
                      min="0" 
                      max="1" 
                      step="0.1" 
                      defaultValue={layer.opacity || 0.8}
                      className="w-full h-1 bg-background-light rounded-lg appearance-none cursor-pointer"
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => handleOpacityChange(e, layer.id, parseFloat(e.target.value))}
                    />
                    <span className="text-xs text-google-grey-300 w-8">
                      {Math.round((layer.opacity || 0.8) * 100)}%
                    </span>
                  </div>
                  
                  {/* Layer metadata preview */}
                  {layer.latitude && layer.longitude && (
                    <div className="mt-2 text-xs text-google-grey-300">
                      <div className="grid grid-cols-2 gap-1">
                        <span>Latitude:</span>
                        <span className="text-google-grey-200">{layer.latitude.toFixed(4)}</span>
                        <span>Longitude:</span>
                        <span className="text-google-grey-200">{layer.longitude.toFixed(4)}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
};

LayersList.propTypes = {
  showNotification: PropTypes.func.isRequired,
  onLayerSelect: PropTypes.func,
  selectedLayerId: PropTypes.string
};

export default LayersList;