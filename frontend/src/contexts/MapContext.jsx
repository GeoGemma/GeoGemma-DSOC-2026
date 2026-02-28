// src/contexts/MapContext.jsx - Enhanced with satellite basemap support
import { createContext, useContext, useState, useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { useAuth } from './AuthContext';
import { getMapLayers, saveMapLayer, deleteMapLayer, clearUserLayers } from '../services/api';

const MapContext = createContext(null);

export function MapProvider({ children }) {
  const [map, setMap] = useState(null);
  const [layers, setLayers] = useState([]);
  const [markers, setMarkers] = useState([]);
  const [drawnFeatures, setDrawnFeatures] = useState([]); // State for drawn features
  const [currentBasemap, setCurrentBasemap] = useState('dark'); // 'dark' or 'satellite'
  const mapInitializedRef = useRef(false);
  const { currentUser } = useAuth();
  
  // Store map position
  const [mapState, setMapState] = useState({
    center: [0, 0],
    zoom: 2,
    lastGeocodedLocation: null,
    lastGeocodedCoords: null,
  });

  useEffect(() => {
    return () => {
      // Cleanup map on unmount
      if (map) map.remove();
    };
  }, [map]);

  // Fetch saved layers when user is authenticated
  useEffect(() => {
    const fetchUserLayers = async () => {
      if (currentUser && currentUser.uid) {
        try {
          console.log(`Fetching layers for user ${currentUser.uid}`);
          const response = await getMapLayers(currentUser.uid);
          
          if (response.success && response.data && Array.isArray(response.data)) {
            // Sort by timestamp if available, newest first
            const sortedLayers = [...response.data].sort((a, b) => 
              (b.timestamp || 0) - (a.timestamp || 0)
            );
            
            // Don't replace layers if there are no saved layers
            if (sortedLayers.length > 0) {
              console.log(`Loaded ${sortedLayers.length} layers from Firestore`);
              setLayers(sortedLayers);
              
              // Add each layer to the map if it exists
              if (map) {
                // Clear existing layers first to avoid duplicates
                layers.forEach(layer => {
                  const layerId = `ee-layer-${layer.id}`;
                  const sourceId = `ee-source-${layer.id}`;
                  
                  if (map.getLayer(layerId)) {
                    map.removeLayer(layerId);
                  }
                  if (map.getSource(sourceId)) {
                    map.removeSource(sourceId);
                  }
                });
                
                // Add the loaded layers to the map (in reverse so newest is on top)
                [...sortedLayers].reverse().forEach(layer => {
                  if (layer.tile_url) {
                    addLayerToMap(map, layer, `ee-source-${layer.id}`, `ee-layer-${layer.id}`, setLayers);
                  }
                });
              }
            }
          } else {
            console.log('No saved layers found or error fetching layers');
          }
        } catch (error) {
          console.error('Error fetching user layers:', error);
        }
      }
    };
    
    fetchUserLayers();
  }, [currentUser, map]);

  // Initialize map with dark theme or satellite imagery
  const initializeMap = (container) => {
    if (mapInitializedRef.current) return;
    
    // Define basemap styles
    const basemapStyles = {
      dark: {
        version: 8,
        name: 'Dark',
        sources: {
          'raster-tiles': {
            type: 'raster',
            tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          }
        },
        layers: [
          {
            id: 'dark-tiles',
            type: 'raster',
            source: 'raster-tiles',
            minzoom: 0,
            maxzoom: 22
          }
        ]
      },
      satellite: {
        version: 8,
        name: 'Satellite',
        sources: {
          'satellite-tiles': {
            type: 'raster',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.esri.com/">Esri</a> &copy; <a href="https://www.maxar.com/">Maxar</a>'
          }
        },
        layers: [
          {
            id: 'satellite-tiles',
            type: 'raster',
            source: 'satellite-tiles',
            minzoom: 0,
            maxzoom: 22
          }
        ]
      }
    };
    
    // Use the current basemap style
    const newMap = new maplibregl.Map({
      container,
      style: basemapStyles[currentBasemap],
      center: mapState.center,
      zoom: mapState.zoom,
      attributionControl: false
    });

    // Add map controls
    newMap.addControl(new maplibregl.AttributionControl({ compact: true }));
    newMap.addControl(new maplibregl.NavigationControl(), 'top-left');
    newMap.addControl(new maplibregl.FullscreenControl());
    newMap.addControl(new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: true
    }));
    newMap.addControl(new maplibregl.ScaleControl());

    newMap.on('load', () => {
      // Store map position on movement
      newMap.on('moveend', () => {
        setMapState(prev => ({
          ...prev,
          center: newMap.getCenter().toArray(),
          zoom: newMap.getZoom()
        }));
      });
    });

    setMap(newMap);
    mapInitializedRef.current = true;
  };

  // Set basemap type (dark or satellite)
  const setBasemap = (basemapId) => {
    if (!map || !basemapId || basemapId === currentBasemap) return;
    
    // Define basemap styles
    const basemapStyles = {
      dark: {
        version: 8,
        name: 'Dark',
        sources: {
          'raster-tiles': {
            type: 'raster',
            tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          }
        },
        layers: [
          {
            id: 'dark-tiles',
            type: 'raster',
            source: 'raster-tiles',
            minzoom: 0,
            maxzoom: 22
          }
        ]
      },
      satellite: {
        version: 8,
        name: 'Satellite',
        sources: {
          'satellite-tiles': {
            type: 'raster',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.esri.com/">Esri</a> &copy; <a href="https://www.maxar.com/">Maxar</a>'
          }
        },
        layers: [
          {
            id: 'satellite-tiles',
            type: 'raster',
            source: 'satellite-tiles',
            minzoom: 0,
            maxzoom: 22
          }
        ]
      }
    };
    
    // Save the current map state
    const center = map.getCenter();
    const zoom = map.getZoom();
    const bearing = map.getBearing();
    const pitch = map.getPitch();
    
    // Update the basemap
    map.setStyle(basemapStyles[basemapId]);
    
    // When style is loaded, restore the layers
    map.once('styledata', () => {
      // Restore map state
      map.setCenter(center);
      map.setZoom(zoom);
      map.setBearing(bearing);
      map.setPitch(pitch);
      
      // Re-add all layers that were on the map
      layers.forEach(layer => {
        const sourceId = `ee-source-${layer.id}`;
        const layerId = `ee-layer-${layer.id}`;
        
        if (layer.tile_url) {
          addLayerToMap(map, layer, sourceId, layerId, setLayers);
        }
      });
    });
    
    // Update state
    setCurrentBasemap(basemapId);
  };

  const addLayer = async (layerData) => {
    if (!map) {
      console.error("Map is not initialized yet");
      return;
    }
    
    console.log("Adding layer:", layerData);
    
    const sourceId = `ee-source-${layerData.id}`;
    const layerId = `ee-layer-${layerData.id}`;
  
    try {
      // Remove existing layer/source if they exist
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
  
      // Ensure the map is completely loaded before adding layers
      if (!map.loaded()) {
        console.log("Map not fully loaded, waiting...");
        map.once('load', () => {
          addLayerToMap(map, layerData, sourceId, layerId, setLayers);
        });
      } else {
        addLayerToMap(map, layerData, sourceId, layerId, setLayers);
      }
      
      // Save layer to Firestore if user is authenticated
      if (currentUser && currentUser.uid) {
        try {
          // Add timestamp for sorting
          const layerWithTimestamp = {
            ...layerData,
            timestamp: Date.now()
          };
          
          await saveMapLayer(currentUser.uid, layerData.id, layerWithTimestamp);
          console.log(`Layer ${layerData.id} saved to Firestore`);
        } catch (error) {
          console.error('Error saving layer to Firestore:', error);
        }
      }
    } catch (error) {
      console.error("Error in addLayer:", error);
    }
  };
  
  // Enhanced addLayerToMap function with better support for gas and fire layers
  const addLayerToMap = (mapInstance, layerData, sourceId, layerId, setLayersFn) => {
    try {
      console.log(`Adding source: ${sourceId} with URL: ${layerData.tile_url}`);
      
      // Add the source for the layer
      mapInstance.addSource(sourceId, {
        'type': 'raster',
        'tiles': [layerData.tile_url],
        'tileSize': 256
      });
      
      console.log(`Adding layer: ${layerId}`);
      
      // Determine layer type for special handling
      const processingType = layerData.processing_type ? layerData.processing_type.toUpperCase() : '';
      const isGasLayer = ['CO', 'NO2', 'CH4', 'SO2'].includes(processingType) || 
                        (layerData.metadata && layerData.metadata.gas_type);
      const isFireLayer = ['ACTIVE_FIRE', 'ACTIVE FIRE', 'BURN_SEVERITY', 'BURN SEVERITY'].includes(processingType) ||
                         (layerData.metadata && layerData.metadata.SOURCE_DATASET && 
                          layerData.metadata.SOURCE_DATASET.includes('FIRMS'));
      
      // Specialized layer paint properties based on type
      let paintProps = {
        'raster-opacity': layerData.opacity || 0.8
      };
      
      // Add special paint properties for fire or gas layers if needed
      if (isFireLayer) {
        // Enhance fire visibility
        paintProps['raster-saturation'] = 0.5; // Increase color saturation
        paintProps['raster-contrast'] = 0.2;   // Slight increase in contrast
      } else if (isGasLayer) {
        // Enhance gas concentration visibility  
        paintProps['raster-saturation'] = 0.3;
        paintProps['raster-contrast'] = 0.1;
        paintProps['raster-brightness-min'] = 0.1; // Help with dark areas
      }
      
      // Add the layer
      mapInstance.addLayer({
        'id': layerId,
        'type': 'raster',
        'source': sourceId,
        'paint': paintProps,
        'layout': {
          'visibility': layerData.visibility || 'visible'
        }
      });
      
      console.log(`Layer added successfully: ${layerId}`);
      
      // Process metadata for specialized layer types
      let enhancedLayerData = {...layerData};
      
      // Normalize gas-specific metadata 
      if (isGasLayer) {
        // Extract gas type from processing_type or metadata
        let gasType = processingType;
        if (layerData.metadata && layerData.metadata.gas_type) {
          gasType = layerData.metadata.gas_type.toUpperCase();
        }
        
        // Ensure standard gas information is available
        if (!enhancedLayerData.metadata) {
          enhancedLayerData.metadata = {};
        }
        
        // Add gas-specific identifier for legend selection
        enhancedLayerData.metadata.gas_type = gasType;
        
        // Set standard processing_type to help with legend matching
        if (!['CO', 'NO2', 'CH4', 'SO2'].includes(enhancedLayerData.processing_type)) {
          enhancedLayerData.processing_type = gasType;
        }
      }
      
      // Normalize fire-specific metadata
      if (isFireLayer) {
        if (!enhancedLayerData.metadata) {
          enhancedLayerData.metadata = {};
        }
        
        // Standardize processing_type for fire layers
        if (!['ACTIVE_FIRE', 'ACTIVE FIRE', 'BURN SEVERITY'].includes(enhancedLayerData.processing_type)) {
          enhancedLayerData.processing_type = 'ACTIVE FIRE';
        }
      }
      
      // Update state with new layer - putting most recent layer at the TOP of the array
      setLayersFn(prev => {
        // Remove any existing layer with same id
        const filtered = prev.filter(layer => layer.id !== enhancedLayerData.id);
        // Add new layer at the beginning of the array (top of the stack)
        return [enhancedLayerData, ...filtered];
      });
    } catch (error) {
      console.error(`Error adding layer ${layerId} to map:`, error);
    }
  };

  const removeLayer = async (layerId) => {
    if (!map) return;
    
    const mapLayerId = `ee-layer-${layerId}`;
    const mapSourceId = `ee-source-${layerId}`;

    if (map.getLayer(mapLayerId)) {
      map.removeLayer(mapLayerId);
    }
    
    if (map.getSource(mapSourceId)) {
      map.removeSource(mapSourceId);
    }

    setLayers(prev => prev.filter(layer => layer.id !== layerId));
    
    // Remove from Firestore if user is authenticated
    if (currentUser && currentUser.uid) {
      try {
        await deleteMapLayer(currentUser.uid, layerId);
        console.log(`Layer ${layerId} removed from Firestore`);
      } catch (error) {
        console.error('Error removing layer from Firestore:', error);
      }
    }
  };

  const clearLayers = async () => {
    if (!map) return;
    // Remove all layers from the map
    layers.forEach(layer => {
      const layerId = `ee-layer-${layer.id}`;
      const sourceId = `ee-source-${layer.id}`;
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    });
    setLayers([]);
    clearMarkers();
    // Clear layers from Firestore if the user is authenticated
    if (currentUser && currentUser.uid) {
      try {
        // Permanently delete each layer, like the individual delete button
        for (const layer of layers) {
          await deleteMapLayer(currentUser.uid, layer.id);
        }
        await clearUserLayers(currentUser.uid); // Optionally clear any remaining
      } catch (error) {
        console.error('Error calling clearUserLayers:', error);
      }
    }
  };

  const toggleLayerVisibility = (layerId) => {
    if (!map) return;
    
    const mapLayerId = `ee-layer-${layerId}`;
    
    if (map.getLayer(mapLayerId)) {
      const currentVisibility = map.getLayoutProperty(mapLayerId, 'visibility');
      const newVisibility = currentVisibility === 'visible' ? 'none' : 'visible';
      
      map.setLayoutProperty(mapLayerId, 'visibility', newVisibility);
      
      setLayers(prev => prev.map(layer => 
        layer.id === layerId 
          ? { ...layer, visibility: newVisibility } 
          : layer
      ));
      
      // Update in Firestore if user is authenticated
      if (currentUser && currentUser.uid) {
        const updatedLayer = layers.find(layer => layer.id === layerId);
        if (updatedLayer) {
          try {
            saveMapLayer(currentUser.uid, layerId, {
              ...updatedLayer,
              visibility: newVisibility
            });
          } catch (error) {
            console.error('Error updating layer visibility in Firestore:', error);
          }
        }
      }
    }
  };

  const setLayerOpacity = (layerId, opacity) => {
    if (!map) return;
    
    const mapLayerId = `ee-layer-${layerId}`;
    
    if (map.getLayer(mapLayerId)) {
      map.setPaintProperty(mapLayerId, 'raster-opacity', opacity);
      
      setLayers(prev => prev.map(layer => 
        layer.id === layerId 
          ? { ...layer, opacity } 
          : layer
      ));
      
      // Update in Firestore if user is authenticated
      if (currentUser && currentUser.uid) {
        const updatedLayer = layers.find(layer => layer.id === layerId);
        if (updatedLayer) {
          try {
            saveMapLayer(currentUser.uid, layerId, {
              ...updatedLayer,
              opacity
            });
          } catch (error) {
            console.error('Error updating layer opacity in Firestore:', error);
          }
        }
      }
    }
  };
  
  // Filter layer data by range
  const filterLayerByRange = (layerId, min, max, enabled) => {
    if (!map) return;
    
    const layerIndex = layers.findIndex(layer => layer.id === layerId);
    if (layerIndex === -1) return;
    
    const mapLayerId = `ee-layer-${layerId}`;
    
    if (map.getLayer(mapLayerId)) {
      console.log(`Filtering ${layerId} to range: ${min}-${max}, enabled: ${enabled}`);
      
      // Store filter info on the layer for future reference
      const updatedLayers = [...layers];
      updatedLayers[layerIndex] = {
        ...updatedLayers[layerIndex],
        filter: { min, max, enabled }
      };
      
      // Apply a visual indicator for filtering 
      if (enabled) {
        // Apply visual effects to indicate filtering is active
        // This is just a visual indicator until actual raster filtering is implemented
        map.setPaintProperty(mapLayerId, 'raster-saturation', -0.2);
        map.setPaintProperty(mapLayerId, 'raster-contrast', 0.2);
      } else {
        // Reset when filter is disabled
        map.setPaintProperty(mapLayerId, 'raster-saturation', 0);
        map.setPaintProperty(mapLayerId, 'raster-contrast', 0);
      }
      
      setLayers(updatedLayers);
      
      // Update in Firestore if user is authenticated
      if (currentUser && currentUser.uid) {
        try {
          saveMapLayer(currentUser.uid, layerId, updatedLayers[layerIndex]);
        } catch (error) {
          console.error('Error updating layer filter in Firestore:', error);
        }
      }
    }
  };
  
  // Function to reorder layers
  const reorderLayers = (newLayerOrder) => {
    if (!map) return;
    
    // First, save all the layer data
    const layerData = newLayerOrder.map(layer => ({
      id: layer.id,
      tile_url: layer.tile_url,
      opacity: layer.opacity || 0.8,
      visibility: layer.visibility || 'visible',
      location: layer.location,
      processing_type: layer.processing_type,
      latitude: layer.latitude,
      longitude: layer.longitude,
      metadata: layer.metadata,
      timestamp: layer.timestamp || Date.now()
    }));
    
    // Remove all layers and sources from the map
    layers.forEach(layer => {
      const mapLayerId = `ee-layer-${layer.id}`;
      const mapSourceId = `ee-source-${layer.id}`;
      
      if (map.getLayer(mapLayerId)) {
        map.removeLayer(mapLayerId);
      }
      
      if (map.getSource(mapSourceId)) {
        map.removeSource(mapSourceId);
      }
    });
    
    // Now add layers back to the map in REVERSE order of the UI list
    // This is because in MapLibre, the last added layer appears on top
    // We want the first layer in our UI list to be visually on top
    [...layerData].reverse().forEach(layer => {
      if (layer.tile_url) {
        const sourceId = `ee-source-${layer.id}`;
        const layerId = `ee-layer-${layer.id}`;
        
        // Add the source
        map.addSource(sourceId, {
          'type': 'raster',
          'tiles': [layer.tile_url],
          'tileSize': 256
        });
        
        // Add the layer
        map.addLayer({
          'id': layerId,
          'type': 'raster',
          'source': sourceId,
          'paint': {
            'raster-opacity': layer.opacity
          },
          'layout': {
            'visibility': layer.visibility
          }
        });
      }
    });
    
    // Update the state with the new order
    setLayers(newLayerOrder);
    
    // Update in Firestore if user is authenticated
    if (currentUser && currentUser.uid) {
      try {
        // This would require a batch update operation
        // For now, we'll just update the UI and skip Firestore update
        console.log("Layers reordered successfully in UI (Firestore batch update not implemented)");
      } catch (error) {
        console.error('Error updating layer order in Firestore:', error);
      }
    }
    
    console.log("Layers reordered successfully");
  };

  // Helper for zoom level based on processing type
  const getAppropriateZoomLevel = (processingType) => {
    switch (processingType) {
      case 'RGB':
        return 12;
      case 'NDVI':
        return 11;
      case 'SURFACE WATER':
        return 9;
      case 'LULC':
        return 10;
      case 'LST':
        return 9;
      case 'OPEN BUILDINGS':
        return 14;
      case 'SAR FLOOD':
        return 10;
      case 'FOREST LOSS':
        return 10;
      case 'FOREST GAIN':
        return 10;
      // New types
      case 'ACTIVE FIRE':
      case 'ACTIVE_FIRE':
      case 'BURN SEVERITY':
      case 'BURN_SEVERITY':
        return 8; // Fire data typically viewed at regional scale
      case 'CO':
      case 'NO2':
      case 'CH4':
      case 'SO2':
        return 7; // Gas concentrations typically viewed at broader scale
      default:
        return 10;
    }
  };

  // Focus on a specific layer
  const focusOnLayer = (layerId) => {
    if (!map || !layerId) return;
    
    // Find the layer data
    const layer = layers.find(l => l.id === layerId);
    if (!layer) {
      console.error(`Layer with ID ${layerId} not found`);
      return;
    }
    
    try {
      console.log("Focusing on layer with metadata:", layer.metadata);
      
      // First priority: Check for 'GEOMETRY CENTROID' field in the exact format from ee_metadata.py
      if (layer.metadata && layer.metadata['GEOMETRY CENTROID']) {
        const centroidStr = layer.metadata['GEOMETRY CENTROID'];
        console.log("Found centroid string:", centroidStr);
        
        // Parse using regex that matches the exact format: "Lon: X.XXXX, Lat: Y.YYYY"
        const match = centroidStr.match(/Lon:\s*([-\d.]+),\s*Lat:\s*([-\d.]+)/);
        
        if (match && match.length === 3) {
          const lon = parseFloat(match[1]);
          const lat = parseFloat(match[2]);
          
          if (!isNaN(lon) && !isNaN(lat)) {
            // Get appropriate zoom level based on layer type
            let zoomLevel = getAppropriateZoomLevel(layer.processing_type);
            
            console.log(`Flying to layer ${layerId} using parsed centroid: Lon=${lon}, Lat=${lat}, Zoom=${zoomLevel}`);
            map.flyTo({
              center: [lon, lat],
              zoom: zoomLevel,
              duration: 1000
            });
            return;
          }
        }
      }
      
      // Second priority: Check for direct coordinates in layer object
      if (layer.latitude !== undefined && layer.longitude !== undefined) {
        const lat = parseFloat(layer.latitude);
        const lon = parseFloat(layer.longitude);
        
        if (!isNaN(lat) && !isNaN(lon)) {
          let zoomLevel = getAppropriateZoomLevel(layer.processing_type);
          
          console.log(`Flying to layer ${layerId} using layer coords: Lon=${lon}, Lat=${lat}, Zoom=${zoomLevel}`);
          map.flyTo({
            center: [lon, lat],
            zoom: zoomLevel,
            duration: 1000
          });
          return;
        }
      }
      
      // Third priority: Check for REQUEST_CENTER coordinates
      if (layer.metadata && layer.metadata.REQUEST_CENTER_LON && layer.metadata.REQUEST_CENTER_LAT) {
        const lon = parseFloat(layer.metadata.REQUEST_CENTER_LON);
        const lat = parseFloat(layer.metadata.REQUEST_CENTER_LAT);
        
        if (!isNaN(lon) && !isNaN(lat)) {
          let zoomLevel = getAppropriateZoomLevel(layer.processing_type);
          
          console.log(`Flying to layer ${layerId} using request center: Lon=${lon}, Lat=${lat}, Zoom=${zoomLevel}`);
          map.flyTo({
            center: [lon, lat],
            zoom: zoomLevel,
            duration: 1000
          });
          return;
        }
      }
      
      console.warn(`Couldn't find usable coordinates for layer ${layerId}`);
      console.log("Available metadata:", layer.metadata);
    } catch (error) {
      console.error(`Error focusing on layer ${layerId}:`, error);
    }
  };

  const addMarker = (lat, lon) => {
    if (!map) return;
    
    // Clear existing markers
    clearMarkers();
    
    // Add new marker
    const newMarker = new maplibregl.Marker()
      .setLngLat([lon, lat])
      .addTo(map);
    
    setMarkers([newMarker]);
  };

  const clearMarkers = () => {
    // Remove all existing markers
    markers.forEach(marker => marker.remove());
    setMarkers([]);
  };

  const flyToLocation = (location, lat, lon, zoom = 10) => {
    if (!map) return;
    
    // Set default zoom level if not already at a good zoom level
    const targetZoom = mapState.zoom < 8 ? zoom : mapState.zoom;
    
    map.flyTo({
      center: [lon, lat],
      zoom: targetZoom,
      duration: 2000
    });
    
    // Update stored coordinates for this location
    setMapState(prev => ({
      ...prev,
      lastGeocodedLocation: location,
      lastGeocodedCoords: [lat, lon]
    }));
  };

  // ---------- DRAWING TOOLS FUNCTIONS ----------

  // Add a drawn feature to the map
  const addDrawnFeature = (feature) => {
    if (!map) return;
    
    // Generate a unique ID for the feature if it doesn't have one
    if (!feature.id) {
      feature.id = `drawn-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    }
    
    // Add to state
    setDrawnFeatures(prev => [...prev, feature]);
    
    // Render all drawn features
    renderDrawnFeatures([...drawnFeatures, feature]);
    
    return feature.id;
  };
  
  // Update an existing drawn feature
  const updateDrawnFeature = (featureId, newFeature) => {
    if (!map || !featureId) return;
    
    // Update in state
    setDrawnFeatures(prev => prev.map(f => 
      f.id === featureId ? { ...newFeature, id: featureId } : f
    ));
    
    // Re-render all features
    renderDrawnFeatures(drawnFeatures.map(f => 
      f.id === featureId ? { ...newFeature, id: featureId } : f
    ));
  };
  
  // Remove a drawn feature
  const removeDrawnFeature = (featureId) => {
    if (!map || !featureId) return;
    
    // Remove from state
    setDrawnFeatures(prev => prev.filter(f => f.id !== featureId));
    
    // Re-render remaining features
    renderDrawnFeatures(drawnFeatures.filter(f => f.id !== featureId));
  };
  
  // Clear all drawn features
  const clearDrawnFeatures = () => {
    if (!map) return;
    
    // Clear state
    setDrawnFeatures([]);
    
    // Remove all drawing layers
    if (map.getLayer('drawn-points')) map.removeLayer('drawn-points');
    if (map.getLayer('drawn-lines')) map.removeLayer('drawn-lines');
    if (map.getLayer('drawn-polygons-fill')) map.removeLayer('drawn-polygons-fill');
    if (map.getLayer('drawn-polygons-outline')) map.removeLayer('drawn-polygons-outline');
    if (map.getSource('drawn-features')) map.removeSource('drawn-features');
  };
  
  // Render all drawn features
  const renderDrawnFeatures = (features) => {
    if (!map || !features.length) return;
    
    // Remove existing layers
    if (map.getLayer('drawn-points')) map.removeLayer('drawn-points');
    if (map.getLayer('drawn-lines')) map.removeLayer('drawn-lines');
    if (map.getLayer('drawn-polygons-fill')) map.removeLayer('drawn-polygons-fill');
    if (map.getLayer('drawn-polygons-outline')) map.removeLayer('drawn-polygons-outline');
    if (map.getSource('drawn-features')) map.removeSource('drawn-features');
    
    // Add source for all features
    map.addSource('drawn-features', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: features
      }
    });
    
    // Add layers for each geometry type
    // Point layer
    map.addLayer({
      id: 'drawn-points',
      source: 'drawn-features',
      type: 'circle',
      filter: ['==', ['geometry-type'], 'Point'],
      paint: {
        'circle-radius': 6,
        'circle-color': ['get', 'color'],
        'circle-stroke-width': 2,
        'circle-stroke-color': '#ffffff'
      }
    });
    
    // Line layer
    map.addLayer({
      id: 'drawn-lines',
      source: 'drawn-features',
      type: 'line',
      filter: ['==', ['geometry-type'], 'LineString'],
      paint: {
        'line-color': ['get', 'color'],
        'line-width': 3
      }
    });
    
    // Polygon fill layer
    map.addLayer({
      id: 'drawn-polygons-fill',
      source: 'drawn-features',
      type: 'fill',
      filter: ['==', ['geometry-type'], 'Polygon'],
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.3
      }
    });
    
    // Polygon outline layer
    map.addLayer({
      id: 'drawn-polygons-outline',
      source: 'drawn-features',
      type: 'line',
      filter: ['==', ['geometry-type'], 'Polygon'],
      paint: {
        'line-color': ['get', 'color'],
        'line-width': 2
      }
    });
  };
  
  // Get all drawn features
  const getDrawnFeatures = () => {
    return drawnFeatures;
  };
  
  // Export drawn features as GeoJSON
  const exportDrawnFeatures = () => {
    if (!drawnFeatures.length) return null;
    
    return {
      type: 'FeatureCollection',
      features: drawnFeatures
    };
  };
  
  // Import GeoJSON as drawn features
  const importDrawnFeatures = (geojson) => {
    if (!map || !geojson || !geojson.features) return;
    
    // Add IDs if not present
    const featuresWithIds = geojson.features.map(f => ({
      ...f,
      id: f.id || `imported-${Date.now()}-${Math.floor(Math.random() * 1000)}`
    }));
    
    // Set state
    setDrawnFeatures(featuresWithIds);
    
    // Render
    renderDrawnFeatures(featuresWithIds);
  };

  const value = {
    map,
    initializeMap,
    layers,
    addLayer,
    removeLayer,
    clearLayers,
    toggleLayerVisibility,
    setLayerOpacity,
    filterLayerByRange,
    reorderLayers,
    focusOnLayer,
    addMarker,
    clearMarkers,
    flyToLocation,
    mapState,
    currentBasemap,
    setBasemap,
    // Drawing tools functions
    addDrawnFeature,
    updateDrawnFeature,
    removeDrawnFeature,
    clearDrawnFeatures,
    renderDrawnFeatures,
    getDrawnFeatures,
    exportDrawnFeatures,
    importDrawnFeatures,
    drawnFeatures
  };

  return <MapContext.Provider value={value}>{children}</MapContext.Provider>;
}

export function useMap() {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error('useMap must be used within a MapProvider');
  }
  return context;
}