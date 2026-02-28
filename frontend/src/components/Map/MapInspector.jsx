// src/components/Map/MapInspector.jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { useMap } from '../../contexts/MapContext';
import usePixelValues from '../../hooks/usePixelValues';
import { 
  Crosshair, 
  BarChart4, 
  LineChart, 
  Info, 
  PinOff, 
  Pin,
  Download,
  AlertTriangle
} from 'lucide-react';
import '../../styles/mapInspector.css';
import axios from 'axios';
import { createTimeSeriesAnalysis } from '../../services/api';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'https://geogemma-backend-312711753493.us-central1.run.app';

const MapInspector = ({ showNotification }) => {
  const { map, layers, selectedLayerId, selectLayer } = useMap();
  const { pixelValues, isLoading, error, fetchPixelValue, clearPixelValues } = usePixelValues();
  
  const [isInspecting, setIsInspecting] = useState(false);
  const [inspectPoint, setInspectPoint] = useState(null);
  const [activeTab, setActiveTab] = useState('values'); // 'values', 'histogram'
  const [isPinned, setIsPinned] = useState(false);
  const chartRef = useRef(null);
  const histogramRef = useRef(null);
  const [histogramData, setHistogramData] = useState(null);
  const [histogramLoading, setHistogramLoading] = useState(false);
  const [histogramError, setHistogramError] = useState(null);

  // Get the active layer based on selectedLayerId
  const activeLayer = layers.find(layer => layer.id === selectedLayerId) || 
                     (layers.length > 0 ? layers.filter(l => l.visibility !== 'none')[0] : null);

  // Update charts when they become visible
  useEffect(() => {
    if (activeTab === 'histogram' && histogramRef.current) {
      renderHistogram();
    }
  }, [activeTab, activeLayer]);

  // Clean up when component unmounts or when inspection mode is turned off
  useEffect(() => {
    return () => {
      if (!isInspecting) {
        clearPixelValues();
      }
    };
  }, [isInspecting, clearPixelValues]);

  // Handle map clicks for inspection
  useEffect(() => {
    if (!map || !isInspecting || !activeLayer) return;

    const handleMapClick = async (e) => {
      const lngLat = [e.lngLat.lng, e.lngLat.lat];
      setInspectPoint(lngLat);
      
      // Fetch pixel value for active layer
      await fetchPixelValue(activeLayer.id, lngLat);
      
      if (!isPinned) {
        // If not pinned, automatically switch to values tab
        setActiveTab('values');
      }
    };
    
    // Add map click listener
    map.getCanvas().style.cursor = 'crosshair';
    map.on('click', handleMapClick);
    
    return () => {
      map.off('click', handleMapClick);
      map.getCanvas().style.cursor = '';
    };
  }, [map, isInspecting, activeLayer, isPinned, fetchPixelValue]);
  
  // Toggle inspection mode
  const toggleInspect = useCallback(() => {
    const newInspecting = !isInspecting;
    setIsInspecting(newInspecting);
    
    if (!newInspecting) {
      // Turn off inspection mode
      setInspectPoint(null);
      clearPixelValues();
    } else {
      showNotification('Click on the map to inspect pixel values', 'info');
    }
  }, [isInspecting, clearPixelValues, showNotification]);
  
  // Toggle pin status
  const togglePin = useCallback(() => {
    const newPinned = !isPinned;
    setIsPinned(newPinned);
    
    if (newPinned) {
      showNotification('Inspection point pinned. Values will persist when clicking elsewhere.', 'info');
    }
  }, [isPinned, showNotification]);
  
  // Fetch real histogram data from backend
  const fetchHistogramData = useCallback(async () => {
    if (!activeLayer || !map) return;
    setHistogramLoading(true);
    setHistogramError(null);
    setHistogramData(null);
    try {
      // Use current map bounds as geometry (GeoJSON Polygon)
      const bounds = map.getBounds();
      const geometry = {
        type: 'Polygon',
        coordinates: [[
          [bounds.getWest(), bounds.getSouth()],
          [bounds.getEast(), bounds.getSouth()],
          [bounds.getEast(), bounds.getNorth()],
          [bounds.getWest(), bounds.getNorth()],
          [bounds.getWest(), bounds.getSouth()]
        ]]
      };
      const response = await axios.post(`${API_BASE_URL}/api/histogram`, {
        geometry,
        processing_type: activeLayer.processing_type,
        // Optionally add start_date, end_date, band_name, scale
      });
      if (response.data.success && response.data.histogram) {
        setHistogramData(response.data.histogram);
      } else {
        setHistogramError(response.data.message || 'Failed to fetch histogram');
      }
    } catch (err) {
      setHistogramError(err.message || 'Failed to fetch histogram');
    } finally {
      setHistogramLoading(false);
    }
  }, [activeLayer, map]);

  // Fetch histogram when tab is selected or layer changes
  useEffect(() => {
    if (activeTab === 'histogram') {
      fetchHistogramData();
    }
    // eslint-disable-next-line
  }, [activeTab, activeLayer]);

  // Render a histogram
  const renderHistogram = useCallback(() => {
    if (histogramLoading) {
      return <div className="flex items-center justify-center py-4"><div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-google-blue"></div></div>;
    }
    if (histogramError) {
      return <div className="text-google-red text-xs">{histogramError}</div>;
    }
    if (!histogramData) {
      return <div className="text-google-grey-300 text-xs">No histogram data available.</div>;
    }
    // Use real histogram data
    const { bucketMeans, histogram } = histogramData;
    if (!bucketMeans || !histogram) {
      return <div className="text-google-grey-300 text-xs">No histogram data available.</div>;
    }
    // Prepare data for chart
    const maxValue = Math.max(...histogram);
    return (
      <div className="w-full h-48 flex items-end gap-1">
        {bucketMeans.map((mean, i) => (
          <div key={i} style={{ height: `${(histogram[i] / maxValue) * 100}%` }} className="flex-1 bg-google-green/70 rounded-t"></div>
        ))}
      </div>
    );
  }, [histogramData, histogramLoading, histogramError]);
  
  // Helper function to get color for layer type
  const getLayerColor = (type) => {
    const colors = {
      'NDVI': '#81c995', // Google green
      'LST': '#f28b82', // Google red
      'SURFACE WATER': '#8ab4f8', // Google blue
      'LULC': '#fdd663', // Google yellow
      'RGB': '#c58af9', // Purple
      'OPEN BUILDINGS': '#ff8c00' // Orange
    };
    
    return colors[type] || '#8ab4f8';
  };
  
  // Render categorical value (for LULC)
  const renderCategoricalValue = (value) => {
    return (
      <div className="flex items-center">
        <div 
          className="w-3 h-3 rounded-full mr-2" 
          style={{ backgroundColor: getCategoryColor(value.value) }}
        ></div>
        <span>{value.className} (Class {value.value})</span>
      </div>
    );
  };
  
  // Get color for LULC category
  const getCategoryColor = (classId) => {
    const colors = {
      1: '#23A669', // Cultivated Land - green
      2: '#006400', // Forest - dark green
      3: '#B8D293', // Grassland - light green
      4: '#FFBB22', // Shrubland - orange-yellow
      5: '#0064C8', // Water - blue
      6: '#0096A0', // Wetlands - teal
      7: '#B4B4B4', // Tundra - gray
      8: '#FA0000', // Artificial Surface - red
      9: '#F9E39C', // Bareland - tan
      10: '#F0F0F0' // Snow and Ice - white
    };
    
    return colors[classId] || '#CCCCCC';
  };
  
  // Render RGB values
  const renderRGBValues = (value) => {
    return (
      <div className="flex flex-col space-y-1">
        <div className="w-full h-6 rounded-sm mb-2" 
          style={{ 
            backgroundColor: `rgb(${value.r}, ${value.g}, ${value.b})` 
          }}
        ></div>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="flex flex-col">
            <span className="text-google-red">R: {value.r}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-google-green">G: {value.g}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-google-blue">B: {value.b}</span>
          </div>
        </div>
      </div>
    );
  };
  
  // Render numerical value with scale
  const renderNumericalValue = (value) => {
    // Create a scale from min to max
    const percent = (value.value - value.min) / (value.max - value.min) * 100;
    
    return (
      <div className="space-y-1">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium">{value.value} {value.unit}</span>
        </div>
        <div className="w-full h-2 bg-google-bg-lighter rounded-full overflow-hidden">
          <div 
            className="h-full rounded-full" 
            style={{ 
              width: `${percent}%`,
              backgroundColor: getLayerColor(value.type.toUpperCase())
            }}
          ></div>
        </div>
        <div className="flex justify-between text-xs text-google-grey-300">
          <span>{value.min} {value.unit}</span>
          <span>{value.max} {value.unit}</span>
        </div>
      </div>
    );
  };
  
  // Render the pixel value or a user-friendly message
  const renderPixelValue = (value) => {
    if (!value) return <div className="inspector-no-value">No value available.</div>;
    if (value.message) {
      return <div className="inspector-no-value">{value.message}</div>;
    }
    
    // Add an indicator if using mock data
    const isMockData = value.isMock;
    
    if (value.categorical) {
      return (
        <div>
          {renderCategoricalValue(value)}
          {isMockData && (
            <div className="text-xs mt-1 text-google-yellow italic">
              * Using estimated values (could not fetch actual data)
            </div>
          )}
        </div>
      );
    } else if (value.type === 'RGB Values') {
      return (
        <div>
          {renderRGBValues(value)}
          {isMockData && (
            <div className="text-xs mt-1 text-google-yellow italic">
              * Using estimated values (could not fetch actual data)
            </div>
          )}
        </div>
      );
    } else if (value.value !== 'N/A') {
      return (
        <div>
          {renderNumericalValue(value)}
          {isMockData && (
            <div className="text-xs mt-1 text-google-yellow italic">
              * Using estimated values (could not fetch actual data)
            </div>
          )}
        </div>
      );
    } else {
      return (
        <div>
          <span>{value.value}</span>
          {isMockData && (
            <div className="text-xs mt-1 text-google-yellow italic">
              * Using estimated values (could not fetch actual data)
            </div>
          )}
        </div>
      );
    }
  };

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="w-full flex justify-center">
          <div className="flex flex-col items-center space-y-1 mx-auto">
            <button
              onClick={toggleInspect}
              className={`transition-all flex items-center gap-2 px-4 py-2 rounded-full shadow-lg border border-google-bg-light/30
                ${isInspecting ? 'bg-google-blue/10 text-google-blue ring-2 ring-google-blue/30' : 'bg-google-bg-light/60 text-google-grey-200 hover:bg-google-bg-lighter hover:text-google-blue hover:scale-105'}
              `}
              title={isInspecting ? "Stop inspecting" : "Inspect pixel values"}
              aria-label={isInspecting ? "Stop inspecting" : "Inspect pixel values"}
              style={{ transition: 'all 0.2s cubic-bezier(0.4,0,0.2,1)' }}
            >
              <Crosshair size={22} />
              <span className="font-medium text-sm">Inspect</span>
            </button>
          </div>
        </div>
        
        {inspectPoint && (
          <div className="text-xs text-google-grey-200">
            Lon: {inspectPoint[0].toFixed(5)}, Lat: {inspectPoint[1].toFixed(5)}
          </div>
        )}
      </div>
      
      {/* Layer info banner */}
      {activeLayer && (
        <div className="bg-google-bg-lighter rounded-lg px-3 py-2 mb-4">
          <div className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: getLayerColor(activeLayer.processing_type) }}
            ></div>
            <span className="text-sm">Inspecting: <span className="text-google-blue">{activeLayer.location}</span> ({activeLayer.processing_type})</span>
          </div>
        </div>
      )}
      
      {inspectPoint && activeLayer && pixelValues[activeLayer.id] ? (
        <div className="space-y-4">
          {/* Tab navigation */}
          <div className="flex border-b border-google-bg-lighter">
            <button
              className={`py-2 px-4 text-sm font-medium relative ${
                activeTab === 'values' 
                  ? 'text-google-blue' 
                  : 'text-google-grey-200 hover:text-google-grey-100'
              }`}
              onClick={() => setActiveTab('values')}
            >
              Values
              {activeTab === 'values' && (
                <div className="absolute bottom-0 left-0 w-full h-0.5 bg-google-blue"></div>
              )}
            </button>
            <button
              className={`py-2 px-4 text-sm font-medium relative ${
                activeTab === 'histogram' 
                  ? 'text-google-blue' 
                  : 'text-google-grey-200 hover:text-google-grey-100'
              }`}
              onClick={() => setActiveTab('histogram')}
            >
              Histogram
              {activeTab === 'histogram' && (
                <div className="absolute bottom-0 left-0 w-full h-0.5 bg-google-blue"></div>
              )}
            </button>
          </div>
          
          {/* Values tab content */}
          {activeTab === 'values' && (
            <div className="space-y-4">
              {activeLayer && pixelValues[activeLayer.id] && (
                <div key={activeLayer.id} className="bg-google-bg-light rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center">
                      <div 
                        className="w-3 h-3 rounded-full mr-2" 
                        style={{ backgroundColor: getLayerColor(activeLayer.processing_type) }}
                      ></div>
                      <h3 className="text-sm font-medium text-google-grey-100">
                        {activeLayer.location}
                      </h3>
                    </div>
                    <span className="text-xs text-google-grey-300">{pixelValues[activeLayer.id].type}</span>
                  </div>
                  
                  <div className="mt-2">
                    {isLoading ? (
                      <div className="flex items-center justify-center py-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-google-blue"></div>
                      </div>
                    ) : (
                      renderPixelValue(pixelValues[activeLayer.id])
                    )}
                  </div>
                  
                  {error && (
                    <div className="mt-2 text-google-red text-xs flex items-center gap-1">
                      <AlertTriangle size={14} />
                      <span>{error}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
          {/* Histogram tab content */}
          {activeTab === 'histogram' && (
            <div className="bg-google-bg-light rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <BarChart4 size={16} className="text-google-grey-300" />
                  <h3 className="text-sm font-medium text-google-grey-100">
                    Value Distribution
                  </h3>
                </div>
                <button 
                  className="text-xs flex items-center gap-1 text-google-grey-300 hover:text-google-grey-100"
                  onClick={() => showNotification('Download feature coming soon', 'info')}
                >
                  <Download size={14} />
                  <span>Export</span>
                </button>
              </div>
              
              <div>
                {renderHistogram()}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-[300px] text-center">
          {isInspecting ? (
            <div className="space-y-2">
              <Crosshair size={32} className="mx-auto text-google-grey-300/50 mb-2" />
              <p className="text-google-grey-200">Click anywhere on the map to inspect.</p>
              <p className="text-google-grey-300 text-sm">
                Pixel values, time series, and histograms will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-center">
                <Info size={32} className="text-google-grey-300/50" />
              </div>
              <p className="text-google-grey-200">Start the inspector to analyze map data.</p>
              <p className="text-google-grey-300 text-sm">
                Click the <Crosshair size={14} className="inline" /> icon above to begin.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

MapInspector.propTypes = {
  showNotification: PropTypes.func.isRequired
};

export default MapInspector;