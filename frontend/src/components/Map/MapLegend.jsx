// src/components/Map/MapLegend.jsx
import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useMap } from '../../contexts/MapContext';
import { 
  Info, 
  ChevronDown, 
  ChevronUp, 
  BarChart4,
  Flame,      // For fire layers
  Wind        // For gas/air quality layers
} from 'lucide-react';
import MetadataViewer from './MetadataViewer';

const MapLegend = ({ selectedLayer }) => {
  const { layers } = useMap();
  const [activeLayer, setActiveLayer] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    legend: true,
    valueGuide: false,
    metadata: true
  });

  // Legend configurations for different layer types
  const legendConfigs = {
    'NDVI': {
      title: 'Vegetation Index (NDVI)',
      gradient: 'linear-gradient(to right, #CE7E45, #DF923D, #F1B555, #FCD163, #99B718, #74A901, #66A000, #529400, #3E8601, #056201, #004C00)',
      min: -0.2,
      max: 0.8,
      middle: 'Moderate',
      description: 'NDVI measures vegetation density and health using near-infrared and red light reflectance.',
      stats: {
        healthyVeg: '0.6 to 0.8',
        moderateVeg: '0.2 to 0.5',
        sparseVeg: '-0.1 to 0.1'
      }
    },
    'SURFACE WATER': {
      title: 'Surface Water',
      gradient: 'linear-gradient(to right, #ffffff, #d4e7ff, #a8d1ff, #7cbaff, #51a3ff, #258cff, #0075ff, #005ebf, #004080)',
      min: 'None',
      max: 'Permanent',
      middle: 'Seasonal',
      description: 'Surface water detection shows water presence and extent over time.',
      stats: {
        permanent: '90% to 100%',
        seasonal: '40% to 85%',
        rare: '5% to 35%'
      }
    },
    'LST': {
      title: 'Land Surface Temperature',
      gradient: 'linear-gradient(to right, #040274, #307ef3, #30c8e2, #86e26f, #ffd611, #ff8b13, #ff0000)',
      min: '0°C',
      max: '50°C',
      middle: 'Moderate',
      description: 'Land Surface Temperature shows Earth surface thermal conditions.',
      stats: {
        cool: 'Below 15°C',
        moderate: '15°C to 30°C',
        hot: 'Above 30°C'
      }
    },
    'LULC': {
      title: 'Land Use/Land Cover',
      categories: [
        { color: '#006400', label: 'Tree cover' },
        { color: '#ffbb22', label: 'Shrubland' },
        { color: '#ffff4c', label: 'Grassland' },
        { color: '#f096ff', label: 'Cropland' },
        { color: '#fa0000', label: 'Built-up' },
        { color: '#b4b4b4', label: 'Bare/sparse' },
        { color: '#0064c8', label: 'Water' }
      ],
      description: 'Land Use/Land Cover classification shows different surface types and uses.'
    },
    'RGB': {
      title: 'RGB Imagery',
      description: 'True color imagery shows Earth as it would appear to the human eye from space.'
    },
    'OPEN BUILDINGS': {
      title: 'Building Heights',
      gradient: 'linear-gradient(to right, #0000FF, #00FFFF, #00FF00, #FFFF00, #FF8C00, #FF0000)',
      min: 'Low',
      max: 'Tall',
      middle: 'Medium',
      description: 'Building heights data shows the vertical extent of structures.',
      stats: {
        low: '0 to 10m',
        medium: '10 to 25m',
        high: 'Above 25m'
      }
    },
    'FOREST_LOSS': {
      title: 'Forest Loss Year',
      gradient: 'linear-gradient(to right, #ffff00, #ffaa00, #ff5500, #ff0000)',
      min: '1 (2001)',
      max: '23 (2023)',
      middle: '12 (2012)',
      description: 'Year of forest loss detection, from 2001 to 2023. Forest loss is defined as a stand-replacement disturbance or change from forest to non-forest state.',
      stats: {
        early: '1-8 (2001-2008)',
        mid: '9-16 (2009-2016)',
        recent: '17-23 (2017-2023)'
      }
    },
    'FOREST LOSS': {
      title: 'Forest Loss Year',
      gradient: 'linear-gradient(to right, #ffff00, #ffaa00, #ff5500, #ff0000)',
      min: '1 (2001)',
      max: '23 (2023)',
      middle: '12 (2012)',
      description: 'Year of forest loss detection, from 2001 to 2023. Forest loss is defined as a stand-replacement disturbance or change from forest to non-forest state.',
      stats: {
        early: '1-8 (2001-2008)',
        mid: '9-16 (2009-2016)',
        recent: '17-23 (2017-2023)'
      }
    },
    
    // New layers for atmospheric gases
    'CO': {
      title: 'Carbon Monoxide (CO)',
      gradient: 'linear-gradient(to right, black, blue, purple, cyan, green, yellow, red)',
      min: '0',
      max: '0.05',
      middle: 'Moderate',
      description: 'Carbon monoxide (CO) concentration in the atmosphere, measured from Sentinel-5P satellite data.',
      stats: {
        unit: 'mol/m²',
        low: '0 to 0.01',
        moderate: '0.01 to 0.03',
        high: '0.03 to 0.05+'
      },
      icon: <Wind size={16} className="text-google-blue" />
    },
    'NO2': {
      title: 'Nitrogen Dioxide (NO2)',
      gradient: 'linear-gradient(to right, black, blue, purple, cyan, green, yellow, red)',
      min: '0',
      max: '0.0002',
      middle: 'Moderate',
      description: 'Tropospheric nitrogen dioxide (NO2) concentration, primarily from fossil fuel combustion, measured by Sentinel-5P.',
      stats: {
        unit: 'mol/m²',
        low: '0 to 0.00005',
        moderate: '0.00005 to 0.0001',
        high: '0.0001 to 0.0002+'
      },
      icon: <Wind size={16} className="text-google-blue" />
    },
    'CH4': {
      title: 'Methane (CH4)',
      gradient: 'linear-gradient(to right, black, blue, purple, cyan, green, yellow, red)',
      min: '1750',
      max: '1900',
      middle: '1825',
      description: 'Atmospheric methane (CH4) concentration, a potent greenhouse gas, measured by Sentinel-5P satellite.',
      stats: {
        unit: 'ppb (parts per billion)',
        background: '1750 to 1800',
        moderate: '1800 to 1850',
        high: '1850 to 1900+'
      },
      icon: <Wind size={16} className="text-google-blue" />
    },
    'SO2': {
      title: 'Sulfur Dioxide (SO2)',
      gradient: 'linear-gradient(to right, black, blue, purple, cyan, green, yellow, red)',
      min: '0',
      max: '0.0005',
      middle: 'Moderate',
      description: 'Sulfur dioxide (SO2) concentration in the atmosphere, often from volcanic activity and industrial processes, measured by Sentinel-5P.',
      stats: {
        unit: 'mol/m²',
        low: '0 to 0.0001',
        moderate: '0.0001 to 0.0003',
        high: '0.0003 to 0.0005+'
      },
      icon: <Wind size={16} className="text-google-blue" />
    },
    
    // Active fire layers
    'ACTIVE_FIRE': {
      title: 'Active Fire Intensity',
      gradient: 'linear-gradient(to right, red, orange, yellow)',
      min: '325 K',
      max: '400 K',
      middle: '360 K',
      description: 'FIRMS active fire detection based on thermal anomalies. Higher values indicate more intense fires.',
      stats: {
        unit: 'Kelvin (brightness temperature)',
        potential: '325 to 340',
        active: '340 to 370',
        intense: '370 to 400+'
      },
      icon: <Flame size={16} className="text-google-red" />
    },
    'ACTIVE FIRE': {
      title: 'Active Fire Intensity',
      gradient: 'linear-gradient(to right, red, orange, yellow)',
      min: '325 K',
      max: '400 K',
      middle: '360 K',
      description: 'FIRMS active fire detection based on thermal anomalies. Higher values indicate more intense fires.',
      stats: {
        unit: 'Kelvin (brightness temperature)',
        potential: '325 to 340',
        active: '340 to 370',
        intense: '370 to 400+'
      },
      icon: <Flame size={16} className="text-google-red" />
    },
    'BURN SEVERITY': {
      title: 'Active Fire Intensity',
      gradient: 'linear-gradient(to right, red, orange, yellow)',
      min: '325 K',
      max: '400 K',
      middle: '360 K',
      description: 'FIRMS active fire detection based on thermal anomalies. Higher values indicate more intense fires.',
      stats: {
        unit: 'Kelvin (brightness temperature)',
        potential: '325 to 340',
        active: '340 to 370',
        intense: '370 to 400+'
      },
      icon: <Flame size={16} className="text-google-red" />
    }
  };

  // Use the selected layer if provided, otherwise determine based on top visible layer
  useEffect(() => {
    if (selectedLayer) {
      // First try with the exact processing_type
      let config = legendConfigs[selectedLayer.processing_type];
      
      // If not found, try with a case-insensitive match
      if (!config) {
        const processingType = selectedLayer.processing_type.toUpperCase();
        const matchingKey = Object.keys(legendConfigs).find(
          key => key.toUpperCase() === processingType
        );
        if (matchingKey) {
          config = legendConfigs[matchingKey];
        }
      }
      
      // If still not found, check for special gas cases
      if (!config && selectedLayer.metadata && selectedLayer.metadata.gas_type) {
        const gasType = selectedLayer.metadata.gas_type.toUpperCase();
        if (legendConfigs[gasType]) {
          config = legendConfigs[gasType];
        }
      }
      
      // If not found, create a minimal fallback
      if (!config) {
        config = {
          title: selectedLayer.processing_type,
          description: `${selectedLayer.processing_type} data for ${selectedLayer.location}.`
        };
      }
      
      setActiveLayer({
        ...selectedLayer,
        config
      });
      return;
    }
    
    // If no selected layer, determine based on visible layers
    if (!layers || layers.length === 0) {
      setActiveLayer(null);
      return;
    }

    // Get the top-most visible layer
    const visibleLayers = layers.filter(layer => layer.visibility !== 'none');
    if (visibleLayers.length === 0) {
      setActiveLayer(null);
      return;
    }

    // Get the top layer (most recently added)
    const topLayer = visibleLayers[0]; 
    const layerType = topLayer.processing_type;
    
    // Check for matching config - first with exact match
    let layerConfig = legendConfigs[layerType];
    
    // If not found, try with a case-insensitive match
    if (!layerConfig) {
      const upperLayerType = layerType.toUpperCase();
      const matchingKey = Object.keys(legendConfigs).find(
        key => key.toUpperCase() === upperLayerType
      );
      if (matchingKey) {
        layerConfig = legendConfigs[matchingKey];
      }
    }
    
    // Check for special gas metadata
    if (!layerConfig && topLayer.metadata && topLayer.metadata.gas_type) {
      const gasType = topLayer.metadata.gas_type.toUpperCase();
      if (legendConfigs[gasType]) {
        layerConfig = legendConfigs[gasType];
      }
    }
    
    // Set the active layer configuration or use a default
    if (layerConfig) {
      setActiveLayer({
        ...topLayer,
        config: layerConfig
      });
    } else {
      // Create a minimal fallback config
      setActiveLayer({
        ...topLayer,
        config: {
          title: layerType,
          description: `${layerType} data for ${topLayer.location}.`
        }
      });
    }
  }, [layers, selectedLayer]);

  // Toggle section expansion
  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Don't render anything if no layers or no matching legend
  if (!activeLayer) {
    return (
      <div className="flex flex-col items-center justify-center p-4 text-center text-google-grey-300 h-full">
        <Info size={24} className="mb-2 text-google-grey-300/50" />
        <p className="text-sm">No active layers to display information for.</p>
        <p className="text-xs mt-2">Add a layer using the search bar to see details here.</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Layer info header */}
      <div className="mb-4 flex items-start gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            {activeLayer.config.icon}
            <h3 className="text-google-blue text-lg font-medium mb-1">{activeLayer.config?.title || activeLayer.processing_type}</h3>
          </div>
          <p className="text-google-grey-100 text-sm">{activeLayer.location}</p>
        </div>
      </div>

      {/* Legend visualization section with toggle */}
      <div className="bg-google-bg-light rounded-lg p-3 mb-4">
        <div 
          className="flex justify-between items-center cursor-pointer" 
          onClick={() => toggleSection('legend')}
        >
          <h4 className="text-google-grey-200 text-sm font-medium">Legend</h4>
          {expandedSections.legend ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
        
        {expandedSections.legend && (
          <div className="mt-3">
            {/* Gradient bar for continuous data */}
            {activeLayer.config?.gradient && (
              <div className="mb-3">
                <div 
                  className="h-4 w-full rounded"
                  style={{ background: activeLayer.config.gradient }}
                ></div>
                <div className="flex justify-between mt-1 text-xs text-google-grey-300">
                  <span>{activeLayer.config.min}</span>
                  {activeLayer.config.middle && <span>{activeLayer.config.middle}</span>}
                  <span>{activeLayer.config.max}</span>
                </div>
              </div>
            )}

            {/* Categories for discrete data */}
            {activeLayer.config?.categories && (
              <div className="grid grid-cols-1 gap-2">
                {activeLayer.config.categories.map((cat, idx) => (
                  <div 
                    key={idx} 
                    className="flex items-center gap-2"
                  >
                    <div 
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: cat.color }}
                    ></div>
                    <span className="text-xs text-google-grey-100">{cat.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Value Statistics Section */}
      {activeLayer.config?.stats && (
        <div className="bg-google-bg-light rounded-lg p-3 mb-4">
          <div 
            className="flex justify-between items-center cursor-pointer" 
            onClick={() => toggleSection('valueGuide')}
          >
            <h4 className="text-google-grey-200 text-sm font-medium flex items-center gap-2">
              <BarChart4 size={14} />
              <span>Value Guide</span>
            </h4>
            {expandedSections.valueGuide ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
          
          {expandedSections.valueGuide && (
            <div className="mt-3 space-y-2">
              {Object.entries(activeLayer.config.stats).map(([key, value]) => (
                <div key={key} className="grid grid-cols-2 text-xs">
                  <span className="text-google-grey-300 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}:</span>
                  <span className="text-google-grey-100">{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Metadata section with toggle */}
      {activeLayer.metadata && (
        <div className="bg-google-bg-light rounded-lg p-3 mb-4">
          <div 
            className="flex justify-between items-center cursor-pointer" 
            onClick={() => toggleSection('metadata')}
          >
            <h4 className="text-google-grey-200 text-sm font-medium">Metadata</h4>
            {expandedSections.metadata ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
          
          {expandedSections.metadata && (
            <div className="mt-3">
              <MetadataViewer metadata={activeLayer.metadata} />
            </div>
          )}
        </div>
      )}

      {/* Description section */}
      <div className="bg-google-bg-light rounded-lg p-3">
        <h4 className="text-google-grey-200 text-sm font-medium mb-2">About this layer</h4>
        <p className="text-xs text-google-grey-300 leading-normal">
          {activeLayer.config?.description || `This layer shows ${activeLayer.processing_type} data for ${activeLayer.location}.`}
        </p>
      </div>
    </div>
  );
};

MapLegend.propTypes = {
  selectedLayer: PropTypes.object
};

export default MapLegend;