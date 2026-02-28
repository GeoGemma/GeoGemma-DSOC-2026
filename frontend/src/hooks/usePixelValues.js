// src/hooks/usePixelValues.js
import { useState, useCallback } from 'react';
import { useMap } from '../contexts/MapContext';
import axios from 'axios';

// Get base URL from environment variable or default to the deployed backend
const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'https://geogemma-backend-312711753493.us-central1.run.app';

const usePixelValues = () => {
  const { map, layers } = useMap();
  const [isLoading, setIsLoading] = useState(false);
  const [pixelValues, setPixelValues] = useState({});
  const [error, setError] = useState(null);

  /**
   * Fetch pixel values for a specific layer at given coordinates
   * @param {string} layerId - The ID of the layer to get values for
   * @param {Array} coordinates - [longitude, latitude] coordinates
   */
  const fetchPixelValue = useCallback(async (layerId, coordinates) => {
    if (!map || !layerId || !coordinates) {
      setError("Missing required parameters");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const layer = layers.find(l => l.id === layerId);
      if (!layer) {
        setError(`Layer with ID ${layerId} not found`);
        setIsLoading(false);
        return;
      }

      // Make API call to fetch real pixel value
      const response = await axios.post(`${API_BASE_URL}/api/pixel-value`, {
        layer_id: layerId,
        coordinates: coordinates,
        processing_type: layer.processing_type,
        ee_collection_id: layer.metadata?.ee_collection_id,
        image_date: layer.metadata?.IMAGE_DATE || layer.metadata?.['IMAGE DATE']
      });
      
      if (response.data.success) {
        // Format the value based on processing type
        let formattedValue;
        
        switch(layer.processing_type) {
          case 'NDVI':
            formattedValue = {
              type: 'NDVI',
              value: parseFloat(response.data.value).toFixed(3),
              unit: '',
              min: -0.2,
              max: 0.8,
              metadata: layer.metadata
            };
            break;
            
          case 'LST':
            formattedValue = {
              type: 'Land Surface Temperature',
              value: parseFloat(response.data.value).toFixed(1),
              unit: '°C',
              min: 0,
              max: 50,
              metadata: layer.metadata
            };
            break;
            
          case 'SURFACE WATER':
            formattedValue = {
              type: 'Surface Water Occurrence',
              value: Math.round(parseFloat(response.data.value)),
              unit: '%',
              min: 0,
              max: 100,
              metadata: layer.metadata
            };
            break;
            
          case 'LULC':
            // Map class IDs to names
            const lulcClasses = {
              1: 'Cultivated Land',
              2: 'Forest',
              3: 'Grassland',
              4: 'Shrubland',
              5: 'Water',
              6: 'Wetlands',
              7: 'Tundra',
              8: 'Artificial Surface',
              9: 'Bareland',
              10: 'Snow and Ice'
            };
            const classId = parseInt(response.data.value);
            formattedValue = {
              type: 'Land Use / Land Cover',
              value: classId,
              className: lulcClasses[classId] || `Class ${classId}`,
              unit: '',
              categorical: true,
              metadata: layer.metadata
            };
            break;
            
          case 'RGB':
            formattedValue = {
              type: 'RGB Values',
              r: response.data.value.r,
              g: response.data.value.g,
              b: response.data.value.b,
              categorical: false,
              metadata: layer.metadata
            };
            break;
            
          default:
            formattedValue = {
              type: layer.processing_type || 'Unknown',
              value: response.data.value.toString(),
              unit: '',
              metadata: layer.metadata
            };
        }
        
        // Set the value - maintain any previous values for other layers
        setPixelValues(prev => ({
          ...prev,
          [layerId]: formattedValue
        }));
      } else {
        // If backend returns a specific 'no data' message, show it
        if (response.data.message && response.data.message.includes('No') && response.data.message.includes('pixel data')) {
          setPixelValues(prev => ({
            ...prev,
            [layerId]: {
              type: layer.processing_type || 'Unknown',
              value: null,
              message: response.data.message,
              metadata: layer.metadata
            }
          }));
        } else {
          throw new Error(response.data.message || "Failed to fetch pixel value");
        }
      }
    } catch (err) {
      console.error("Error fetching pixel value:", err);
      setError(err.message || "Failed to fetch pixel value");
      
      // Fallback to mock data in case of failure
      const layer = layers.find(l => l.id === layerId);
      const mockValue = generateMockValue(coordinates, layer);
      
      setPixelValues(prev => ({
        ...prev,
        [layerId]: {
          ...mockValue,
          isMock: true // Add flag to indicate this is mock data
        }
      }));
      
      // Show a warning in the console
      console.warn("Using mock data as fallback due to API error");
    } finally {
      setIsLoading(false);
    }
  }, [map, layers]);

  /**
   * Clear pixel values for all or specific layers
   * @param {string} [layerId] - Optional specific layer ID to clear, clears all if not provided
   */
  const clearPixelValues = useCallback((layerId = null) => {
    if (layerId) {
      setPixelValues(prev => {
        const newValues = { ...prev };
        delete newValues[layerId];
        return newValues;
      });
    } else {
      setPixelValues({});
    }
    setError(null);
  }, []);

  // Fallback mock value generator
  const generateMockValue = (coordinates, layer) => {
    // Your existing mock data generation code...
    // This is kept as a fallback for when the API fails
    const [lng, lat] = coordinates;
    const layerType = layer.processing_type;
    
    // Create a deterministic seed from coordinates
    const seed = Math.abs(Math.sin(lng * 100) * Math.cos(lat * 100));
    const normalizedSeed = seed - Math.floor(seed); // Value between 0-1
    
    switch(layerType) {
      case 'NDVI':
        return {
          type: 'NDVI',
          value: (normalizedSeed * 0.9 - 0.2).toFixed(3),
          unit: '',
          min: -0.2,
          max: 0.8,
          metadata: layer.metadata
        };
        
      case 'LST':
        return {
          type: 'Land Surface Temperature',
          value: (normalizedSeed * 40 + 5).toFixed(1),
          unit: '°C',
          min: 0,
          max: 50,
          metadata: layer.metadata
        };
        
      // Include other cases from your original code
      // ...
        
      default:
        return {
          type: layerType || 'Unknown',
          value: normalizedSeed.toFixed(3),
          unit: '',
          metadata: layer.metadata
        };
    }
  };

  return {
    pixelValues,
    isLoading,
    error,
    fetchPixelValue,
    clearPixelValues
  };
};

export default usePixelValues;