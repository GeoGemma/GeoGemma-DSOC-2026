import React, { useState, useEffect, useRef } from 'react';
import { 
  Pencil, 
  Square, 
  Circle, 
  Hexagon, 
  Ruler, 
  Trash2, 
  Undo2, 
  RotateCcw,
  Pointer,
  Save,
  Download,
  ChevronRight,
  ChevronLeft,
  PencilRuler,
  MousePointer,
  Move,
  Info
} from 'lucide-react';
import { useMap } from '../../contexts/MapContext';
import * as turf from '@turf/turf';

const DrawingTools = ({ showNotification }) => {
  // States
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeMode, setActiveMode] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentFeatures, setCurrentFeatures] = useState([]);
  const [drawHistory, setDrawHistory] = useState([]);
  const [measurementInfo, setMeasurementInfo] = useState(null);
  const [activeCategory, setActiveCategory] = useState('draw'); // 'draw', 'measure', 'edit'
  const [animatingButton, setAnimatingButton] = useState(null);
  const [tooltipText, setTooltipText] = useState('');
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [showTooltip, setShowTooltip] = useState(false);
  const [instructionText, setInstructionText] = useState('');
  
  // Refs
  const { map } = useMap();
  const pointsRef = useRef([]);
  const currentFeatureRef = useRef(null);
  const currentSourceRef = useRef(null);
  const currentLayerRef = useRef(null);
  const popupRef = useRef(null);
  const toolbarRef = useRef(null);

  // Draw mode constants
  const DRAW_MODES = {
    SELECT: 'select',
    POINT: 'point',
    LINE: 'line',
    POLYGON: 'polygon',
    RECTANGLE: 'rectangle',
    CIRCLE: 'circle',
    MEASURE: 'measure',
  };

  // Colors for drawing features - using Google palette
  const COLORS = {
    POINT: '#8ab4f8', // Google blue
    LINE: '#8ab4f8', // Google blue
    POLYGON: '#81c995', // Google green
    RECTANGLE: '#c58af9', // Purple
    CIRCLE: '#fdd663', // Google yellow
    MEASURE: '#f28b82' // Google red
  };

  // Initial setup
  useEffect(() => {
    if (!map) return;

    // Clean up on unmount
    return () => {
      cleanupDrawing();
    };
  }, [map]);

  // Handle active draw mode
  useEffect(() => {
    if (!map) return;

    if (activeMode) {
      // Set cursor style based on mode
      map.getCanvas().style.cursor = 
        activeMode === DRAW_MODES.SELECT ? 'pointer' : 'crosshair';
      
      // Set instruction text based on mode
      updateInstructionText(activeMode);
      
      // Add map event listeners for the active mode
      setupEventListeners();
    } else {
      // Reset cursor and remove event listeners
      map.getCanvas().style.cursor = '';
      removeEventListeners();
      setInstructionText('');
    }

    return () => {
      // Clean up event listeners when active mode changes
      removeEventListeners();
    };
  }, [activeMode, map]);

  // Update instruction text based on active mode
  const updateInstructionText = (mode) => {
    switch (mode) {
      case DRAW_MODES.POINT:
        setInstructionText('Click on the map to place a point');
        break;
      case DRAW_MODES.LINE:
        setInstructionText('Click to add line points. Double-click to finish');
        break;
      case DRAW_MODES.POLYGON:
        setInstructionText('Click to add polygon vertices. Double-click to close');
        break;
      case DRAW_MODES.RECTANGLE:
        setInstructionText('Click and drag to draw a rectangle');
        break;
      case DRAW_MODES.CIRCLE:
        setInstructionText('Click and drag to set circle radius');
        break;
      case DRAW_MODES.MEASURE:
        setInstructionText('Click to start measuring. Double-click to finish');
        break;
      case DRAW_MODES.SELECT:
        setInstructionText('Click on a feature to select it');
        break;
      default:
        setInstructionText('');
    }
  };

  // Set up event listeners based on active mode
  const setupEventListeners = () => {
    if (!map) return;

    // Remove existing listeners first
    removeEventListeners();

    // Add appropriate listeners based on mode
    if (activeMode === DRAW_MODES.POINT) {
      map.on('click', handlePointClick);
    } else if (activeMode === DRAW_MODES.LINE || activeMode === DRAW_MODES.POLYGON || activeMode === DRAW_MODES.MEASURE) {
      map.on('click', handleLineOrPolygonClick);
      map.on('mousemove', handleMouseMove);
      map.on('dblclick', handleDoubleClick);
    } else if (activeMode === DRAW_MODES.RECTANGLE) {
      map.on('mousedown', handleRectangleStart);
      map.on('mousemove', handleRectangleMove);
      map.on('mouseup', handleRectangleEnd);
    } else if (activeMode === DRAW_MODES.CIRCLE) {
      map.on('mousedown', handleCircleStart);
      map.on('mousemove', handleCircleMove);
      map.on('mouseup', handleCircleEnd);
    } else if (activeMode === DRAW_MODES.SELECT) {
      map.on('click', handleSelect);
    }
  };

  // Remove all event listeners
  const removeEventListeners = () => {
    if (!map) return;

    map.off('click', handlePointClick);
    map.off('click', handleLineOrPolygonClick);
    map.off('mousemove', handleMouseMove);
    map.off('dblclick', handleDoubleClick);
    map.off('mousedown', handleRectangleStart);
    map.off('mousemove', handleRectangleMove);
    map.off('mouseup', handleRectangleEnd);
    map.off('mousedown', handleCircleStart);
    map.off('mousemove', handleCircleMove);
    map.off('mouseup', handleCircleEnd);
    map.off('click', handleSelect);
  };

  // Handle point drawing
  const handlePointClick = (e) => {
    const coordinates = [e.lngLat.lng, e.lngLat.lat];
    addFeature({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates
      },
      properties: {
        drawType: DRAW_MODES.POINT,
        color: COLORS.POINT
      }
    });
    
    showNotification('Point added', 'success');
  };

  // Handle line or polygon drawing - adds points on click
  const handleLineOrPolygonClick = (e) => {
    const coordinates = [e.lngLat.lng, e.lngLat.lat];
    pointsRef.current.push(coordinates);
    
    updateActiveFeature();
  };

  // Update the currently active feature based on collected points
  const updateActiveFeature = () => {
    // If no points, return
    if (pointsRef.current.length === 0) return;
    
    let geometryType = 'LineString';
    let coordinates = [...pointsRef.current];
    let properties = {
      drawType: activeMode,
      color: activeMode === DRAW_MODES.MEASURE ? COLORS.MEASURE : 
            activeMode === DRAW_MODES.POLYGON ? COLORS.POLYGON : COLORS.LINE
    };
    
    // If it's a polygon, close the shape
    if (activeMode === DRAW_MODES.POLYGON && pointsRef.current.length > 2) {
      geometryType = 'Polygon';
      // Create a closed polygon by adding the first point at the end
      coordinates = [[...pointsRef.current, [...pointsRef.current[0]]]];
    }
    
    // For measurement mode, calculate and display distance
    if (activeMode === DRAW_MODES.MEASURE && pointsRef.current.length > 1) {
      let totalDistance = 0;
      for (let i = 1; i < pointsRef.current.length; i++) {
        const from = turf.point(pointsRef.current[i-1]);
        const to = turf.point(pointsRef.current[i]);
        totalDistance += turf.distance(from, to, {units: 'kilometers'});
      }
      
      properties.measurement = totalDistance;
      setMeasurementInfo({
        distance: totalDistance,
        position: pointsRef.current[pointsRef.current.length - 1]
      });
    }
    
    // Create/update the feature
    const feature = {
      type: 'Feature',
      geometry: {
        type: geometryType,
        coordinates
      },
      properties
    };
    
    // Remove existing temporary feature
    cleanupTemporaryFeature();
    
    // Create a new temporary feature
    currentFeatureRef.current = feature;
    addTemporaryFeature(feature);
  };

  // Handle mouse movement for line/polygon/measure tools to show preview
  const handleMouseMove = (e) => {
    if (pointsRef.current.length > 0) {
        // Create a preview line/polygon that follows the cursor
      const coordinates = [...pointsRef.current, [e.lngLat.lng, e.lngLat.lat]];
      let geometryType = 'LineString';
      let finalCoords = coordinates;
      
      // If it's a polygon with enough points, close the shape in the preview
      if (activeMode === DRAW_MODES.POLYGON && pointsRef.current.length > 1) {
        geometryType = 'Polygon';
        // Create a closed polygon with the moving point
        finalCoords = [[...coordinates, [...pointsRef.current[0]]]];
      }
      
      // For measurement, update the measurement info
      if (activeMode === DRAW_MODES.MEASURE && pointsRef.current.length > 0) {
        let totalDistance = 0;
        for (let i = 1; i < coordinates.length; i++) {
          const from = turf.point(coordinates[i-1]);
          const to = turf.point(coordinates[i]);
          totalDistance += turf.distance(from, to, {units: 'kilometers'});
        }
        
        setMeasurementInfo({
          distance: totalDistance,
          position: [e.lngLat.lng, e.lngLat.lat]
        });
      }
      
      const previewFeature = {
        type: 'Feature',
        geometry: {
          type: geometryType,
          coordinates: finalCoords
        },
        properties: {
          drawType: activeMode,
          isPreview: true,
          color: activeMode === DRAW_MODES.MEASURE ? COLORS.MEASURE : 
                activeMode === DRAW_MODES.POLYGON ? COLORS.POLYGON : COLORS.LINE
        }
      };
      
      // Update the temporary feature
      cleanupTemporaryFeature();
      addTemporaryFeature(previewFeature);
    }
  };

  // Handle double click to complete line/polygon/measure
  const handleDoubleClick = (e) => {
    e.preventDefault(); // Prevent the map from zooming
    
    if (pointsRef.current.length < 2) {
      showNotification('Need at least 2 points to create a shape', 'error');
      return;
    }
    
    // Get the final coordinates
    let geometryType = 'LineString';
    let coordinates = [...pointsRef.current];
    let properties = {
      drawType: activeMode,
      color: activeMode === DRAW_MODES.MEASURE ? COLORS.MEASURE : 
            activeMode === DRAW_MODES.POLYGON ? COLORS.POLYGON : COLORS.LINE
    };
    
    // For polygons, ensure it's closed
    if (activeMode === DRAW_MODES.POLYGON) {
      geometryType = 'Polygon';
      coordinates = [[...coordinates, [...coordinates[0]]]];
    }
    
    // For measurements, calculate the final distance
    if (activeMode === DRAW_MODES.MEASURE) {
      let totalDistance = 0;
      for (let i = 1; i < coordinates.length; i++) {
        const from = turf.point(coordinates[i-1]);
        const to = turf.point(coordinates[i]);
        totalDistance += turf.distance(from, to, {units: 'kilometers'});
      }
      properties.measurement = totalDistance;
      
      // Show a notification with the total distance
      showNotification(`Total distance: ${totalDistance.toFixed(2)} km`, 'info');
    }
    
    // Create the final feature
    const feature = {
      type: 'Feature',
      geometry: {
        type: geometryType,
        coordinates
      },
      properties
    };
    
    // Add it to permanent features
    addFeature(feature);
    
    // Reset drawing state
    pointsRef.current = [];
    setIsDrawing(false);
    setMeasurementInfo(null);
    cleanupTemporaryFeature();
  };

  // Start drawing a rectangle
  const handleRectangleStart = (e) => {
    if (activeMode !== DRAW_MODES.RECTANGLE) return;
    
    setIsDrawing(true);
    pointsRef.current = [[e.lngLat.lng, e.lngLat.lat]];
  };

  // Update rectangle preview during drag
  const handleRectangleMove = (e) => {
    if (activeMode !== DRAW_MODES.RECTANGLE || !isDrawing || pointsRef.current.length === 0) return;
    
    const startPoint = pointsRef.current[0];
    const currentPoint = [e.lngLat.lng, e.lngLat.lat];
    
    // Create a rectangle from the start and current points
    const minX = Math.min(startPoint[0], currentPoint[0]);
    const minY = Math.min(startPoint[1], currentPoint[1]);
    const maxX = Math.max(startPoint[0], currentPoint[0]);
    const maxY = Math.max(startPoint[1], currentPoint[1]);
    
    const coordinates = [
      [minX, minY],
      [maxX, minY],
      [maxX, maxY],
      [minX, maxY],
      [minX, minY]
    ];
    
    const rectangleFeature = {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [coordinates]
      },
      properties: {
        drawType: DRAW_MODES.RECTANGLE,
        isPreview: true,
        color: COLORS.RECTANGLE
      }
    };
    
    // Update the temporary feature
    cleanupTemporaryFeature();
    addTemporaryFeature(rectangleFeature);
  };

  // Finalize rectangle on mouse up
  const handleRectangleEnd = (e) => {
    if (activeMode !== DRAW_MODES.RECTANGLE || !isDrawing || pointsRef.current.length === 0) return;
    
    const startPoint = pointsRef.current[0];
    const currentPoint = [e.lngLat.lng, e.lngLat.lat];
    
    // Skip if the rectangle is too small (likely an accidental click)
    if (Math.abs(startPoint[0] - currentPoint[0]) < 0.0001 && 
        Math.abs(startPoint[1] - currentPoint[1]) < 0.0001) {
      setIsDrawing(false);
      pointsRef.current = [];
      cleanupTemporaryFeature();
      return;
    }
    
    // Create a rectangle from the start and current points
    const minX = Math.min(startPoint[0], currentPoint[0]);
    const minY = Math.min(startPoint[1], currentPoint[1]);
    const maxX = Math.max(startPoint[0], currentPoint[0]);
    const maxY = Math.max(startPoint[1], currentPoint[1]);
    
    const coordinates = [
      [minX, minY],
      [maxX, minY],
      [maxX, maxY],
      [minX, maxY],
      [minX, minY]
    ];
    
    const rectangleFeature = {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [coordinates]
      },
      properties: {
        drawType: DRAW_MODES.RECTANGLE,
        color: COLORS.RECTANGLE
      }
    };
    
    // Add the feature to permanent features
    addFeature(rectangleFeature);
    
    // Reset drawing state
    setIsDrawing(false);
    pointsRef.current = [];
    cleanupTemporaryFeature();
  };

  // Start drawing a circle
  const handleCircleStart = (e) => {
    if (activeMode !== DRAW_MODES.CIRCLE) return;
    
    setIsDrawing(true);
    pointsRef.current = [[e.lngLat.lng, e.lngLat.lat]];
  };

  // Update circle preview during drag
  const handleCircleMove = (e) => {
    if (activeMode !== DRAW_MODES.CIRCLE || !isDrawing || pointsRef.current.length === 0) return;
    
    const center = pointsRef.current[0];
    const currentPoint = [e.lngLat.lng, e.lngLat.lat];
    
    // Calculate radius in kilometers
    const centerPoint = turf.point(center);
    const currentTurfPoint = turf.point(currentPoint);
    const radius = turf.distance(centerPoint, currentTurfPoint, {units: 'kilometers'});
    
    // Convert center to a turf point
    const turfCenter = turf.point(center);
    // Create a circle using turf with the calculated radius
    const turfCircle = turf.circle(turfCenter, radius, {steps: 64});
    
    const circleFeature = {
      ...turfCircle,
      properties: {
        ...turfCircle.properties,
        drawType: DRAW_MODES.CIRCLE,
        isPreview: true,
        color: COLORS.CIRCLE,
        radius: radius
      }
    };
    
    // Update the temporary feature
    cleanupTemporaryFeature();
    addTemporaryFeature(circleFeature);
  };

  // Finalize circle on mouse up
  const handleCircleEnd = (e) => {
    if (activeMode !== DRAW_MODES.CIRCLE || !isDrawing || pointsRef.current.length === 0) return;
    
    const center = pointsRef.current[0];
    const currentPoint = [e.lngLat.lng, e.lngLat.lat];
    
    // Calculate radius in kilometers
    const centerPoint = turf.point(center);
    const currentTurfPoint = turf.point(currentPoint);
    const radius = turf.distance(centerPoint, currentTurfPoint, {units: 'kilometers'});
    
    // Skip if the circle is too small (likely an accidental click)
    if (radius < 0.01) {
      setIsDrawing(false);
      pointsRef.current = [];
      cleanupTemporaryFeature();
      return;
    }
    
    // Convert center to a turf point
    const turfCenter = turf.point(center);
    // Create a circle using turf with the calculated radius
    const turfCircle = turf.circle(turfCenter, radius, {steps: 64});
    
    const circleFeature = {
      ...turfCircle,
      properties: {
        ...turfCircle.properties,
        drawType: DRAW_MODES.CIRCLE,
        color: COLORS.CIRCLE,
        radius: radius,
        center: center
      }
    };
    
    // Add the feature to permanent features
    addFeature(circleFeature);
    
    // Show notification with circle info
    showNotification(`Circle created with radius: ${radius.toFixed(2)} km`, 'success');
    
    // Reset drawing state
    setIsDrawing(false);
    pointsRef.current = [];
    cleanupTemporaryFeature();
  };

  // Handle selecting features
  const handleSelect = (e) => {
    // Implement selection logic
    showNotification('Selection feature coming soon!', 'info');
  };

  // Add a feature to the map
  const addFeature = (feature) => {
    const featureId = Date.now().toString();
    feature.id = featureId;
    
    // Add to features state
    setCurrentFeatures(prev => [...prev, feature]);
    setDrawHistory(prev => [...prev, feature]);
    
    renderFeatures([...currentFeatures, feature]);
  };

  // Add a temporary feature to the map (for previewing)
  const addTemporaryFeature = (feature) => {
    const sourceId = 'temp-source';
    const layerId = 'temp-layer';
    
    // Store refs for cleanup
    currentFeatureRef.current = feature;
    currentSourceRef.current = sourceId;
    currentLayerRef.current = layerId;
    
    // Add source and layer if they don't exist
    if (!map.getSource(sourceId)) {
      map.addSource(sourceId, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [feature]
        }
      });
    } else {
      map.getSource(sourceId).setData({
        type: 'FeatureCollection',
        features: [feature]
      });
    }
    
    // Add layer if it doesn't exist
    if (!map.getLayer(layerId)) {
      // Determine the layer type based on geometry type
      if (feature.geometry.type === 'Point') {
        map.addLayer({
          id: layerId,
          source: sourceId,
          type: 'circle',
          paint: {
            'circle-radius': 6,
            'circle-color': ['get', 'color'],
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff'
          }
        });
      } else if (feature.geometry.type === 'LineString') {
        map.addLayer({
          id: layerId,
          source: sourceId,
          type: 'line',
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 3,
            'line-dasharray': [1, 1]
          }
        });
      } else if (feature.geometry.type === 'Polygon') {
        map.addLayer({
          id: layerId,
          source: sourceId,
          type: 'fill',
          paint: {
            'fill-color': ['get', 'color'],
            'fill-opacity': 0.3,
            'fill-outline-color': ['get', 'color']
          }
        });
        
        // Add an outline layer
        map.addLayer({
          id: `${layerId}-outline`,
          source: sourceId,
          type: 'line',
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 2
          }
        });
      }
    }
  };

  // Cleanup temporary feature
  const cleanupTemporaryFeature = () => {
    if (!map) return;
    
    const layerId = currentLayerRef.current;
    const sourceId = currentSourceRef.current;
    
    if (map.getLayer(`${layerId}-outline`)) {
      map.removeLayer(`${layerId}-outline`);
    }
    
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
    
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }
    
    currentFeatureRef.current = null;
  };

  // Render all features
  const renderFeatures = (features) => {
    if (!map) return;
    
    // Remove existing layers and sources
    if (map.getLayer('draw-layer-points')) map.removeLayer('draw-layer-points');
    if (map.getLayer('draw-layer-lines')) map.removeLayer('draw-layer-lines');
    if (map.getLayer('draw-layer-polygons-fill')) map.removeLayer('draw-layer-polygons-fill');
    if (map.getLayer('draw-layer-polygons-outline')) map.removeLayer('draw-layer-polygons-outline');
    if (map.getSource('draw-source')) map.removeSource('draw-source');
    
    if (features.length === 0) return;
    
    // Create collections for each geometry type
    const pointFeatures = [];
    const lineFeatures = [];
    const polygonFeatures = [];
    
    features.forEach(feature => {
      if (feature.geometry.type === 'Point') {
        pointFeatures.push(feature);
      } else if (feature.geometry.type === 'LineString') {
        lineFeatures.push(feature);
      } else if (feature.geometry.type === 'Polygon') {
        polygonFeatures.push(feature);
      }
    });
    
    // Add source
    map.addSource('draw-source', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: features
      }
    });
    
    // Add layers for each geometry type
    if (pointFeatures.length > 0) {
      map.addLayer({
        id: 'draw-layer-points',
        source: 'draw-source',
        type: 'circle',
        filter: ['==', ['geometry-type'], 'Point'],
        paint: {
          'circle-radius': 6,
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }
      });
    }
    
    if (lineFeatures.length > 0) {
      map.addLayer({
        id: 'draw-layer-lines',
        source: 'draw-source',
        type: 'line',
        filter: ['==', ['geometry-type'], 'LineString'],
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 3
        }
      });
    }
    
    if (polygonFeatures.length > 0) {
      map.addLayer({
        id: 'draw-layer-polygons-fill',
        source: 'draw-source',
        type: 'fill',
        filter: ['==', ['geometry-type'], 'Polygon'],
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': 0.3
        }
      });
      
      map.addLayer({
        id: 'draw-layer-polygons-outline',
        source: 'draw-source',
        type: 'line',
        filter: ['==', ['geometry-type'], 'Polygon'],
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 2
        }
      });
    }
  };

  // Delete all features
  const handleClearAll = () => {
    if (currentFeatures.length === 0) {
      showNotification('No features to clear', 'info');
      return;
    }
    
    setCurrentFeatures([]);
    setDrawHistory([]);
    setMeasurementInfo(null);
    pointsRef.current = [];
    
    if (map) {
      if (map.getLayer('draw-layer-points')) map.removeLayer('draw-layer-points');
      if (map.getLayer('draw-layer-lines')) map.removeLayer('draw-layer-lines');
      if (map.getLayer('draw-layer-polygons-fill')) map.removeLayer('draw-layer-polygons-fill');
      if (map.getLayer('draw-layer-polygons-outline')) map.removeLayer('draw-layer-polygons-outline');
      if (map.getSource('draw-source')) map.removeSource('draw-source');
    }
    
    showNotification('All features cleared', 'success');
    
    // Button animation
    setAnimatingButton('clear');
    setTimeout(() => {
      setAnimatingButton(null);
    }, 300);
  };

  // Undo last action
  const handleUndo = () => {
    if (drawHistory.length === 0) {
      showNotification('Nothing to undo', 'info');
      return;
    }
    
    // Remove the last feature from history
    const newHistory = [...drawHistory.slice(0, -1)];
    setDrawHistory(newHistory);
    setCurrentFeatures(newHistory);
    
    // Redraw features
    renderFeatures(newHistory);
    
    showNotification('Last action undone', 'success');
    
    // Button animation
    setAnimatingButton('undo');
    setTimeout(() => {
      setAnimatingButton(null);
    }, 300);
  };

  // Cancel current drawing
  const handleCancel = () => {
    pointsRef.current = [];
    setIsDrawing(false);
    setMeasurementInfo(null);
    cleanupTemporaryFeature();
    
    showNotification('Drawing cancelled', 'info');
    
    // Button animation
    setAnimatingButton('cancel');
    setTimeout(() => {
      setAnimatingButton(null);
    }, 300);
  };

  // Export features as GeoJSON
  const handleExport = () => {
    if (currentFeatures.length === 0) {
      showNotification('No features to export', 'warning');
      return;
    }
    
    const geojson = {
      type: 'FeatureCollection',
      features: currentFeatures
    };
    
    const json = JSON.stringify(geojson, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = 'geogemma_features.geojson';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showNotification('Features exported as GeoJSON', 'success');
    
    // Button animation
    setAnimatingButton('export');
    setTimeout(() => {
      setAnimatingButton(null);
    }, 300);
  };

  // Clean up all drawing resources
  const cleanupDrawing = () => {
    if (!map) return;
    
    // Remove temporary features
    cleanupTemporaryFeature();
    
    // Remove permanent features
    if (map.getLayer('draw-layer-points')) map.removeLayer('draw-layer-points');
    if (map.getLayer('draw-layer-lines')) map.removeLayer('draw-layer-lines');
    if (map.getLayer('draw-layer-polygons-fill')) map.removeLayer('draw-layer-polygons-fill');
    if (map.getLayer('draw-layer-polygons-outline')) map.removeLayer('draw-layer-polygons-outline');
    if (map.getSource('draw-source')) map.removeSource('draw-source');
    
    // Remove event listeners
    removeEventListeners();
    
    // Reset state
    pointsRef.current = [];
    setActiveMode(null);
    setIsDrawing(false);
    setMeasurementInfo(null);
  };

  // Set the active drawing mode
  const setMode = (mode) => {
    if (activeMode === mode) {
      // Toggle off if already active
      setActiveMode(null);
      map.getCanvas().style.cursor = '';
    } else {
      setActiveMode(mode);
      // Reset drawing state when switching modes
      pointsRef.current = [];
      setIsDrawing(false);
      setMeasurementInfo(null);
      cleanupTemporaryFeature();
    }
  };

  // Toggle the expanded state of the toolbar
  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
    
    // Reset the active category when collapsing
    if (isExpanded) {
      setActiveCategory('draw');
    }
  };
  
  // Handle tooltip for buttons
  const handleMouseEnter = (text, e) => {
    if (!toolbarRef.current) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const toolbarRect = toolbarRef.current.getBoundingClientRect();
    
    // Position tooltip above the button
    setTooltipPosition({
      x: rect.left + rect.width / 2 - toolbarRect.left,
      y: rect.top - toolbarRect.top - 5
    });
    
    setTooltipText(text);
    setShowTooltip(true);
  };
  
  const handleMouseLeave = () => {
    setShowTooltip(false);
  };
  
  // Get button style based on state
  const getButtonStyle = (buttonType, buttonMode = null) => {
    const isActive = buttonMode ? activeMode === buttonMode : false;
    const isAnimating = animatingButton === buttonType;
    
    let baseStyle = "w-10 h-10 flex items-center justify-center rounded-md transition-all";
    
    // Base appearance
    if (isActive) {
      baseStyle += " bg-google-blue/20 text-google-blue";
    } else {
      baseStyle += " bg-google-bg-light hover:bg-google-bg-lighter text-google-grey-200 hover:text-google-grey-100";
    }
    
    // Animation
    if (isAnimating) {
      baseStyle += " animate-pulse";
    }
    
    return baseStyle;
  };
  
  // Render the toolbar with categories
  const renderToolbar = () => {
    return (
      <div 
        className="bg-google-bg border border-google-bg-lighter rounded-lg p-3 shadow-lg"
        ref={toolbarRef}
      >
        {/* Category tabs */}
        <div className="flex mb-3 bg-google-bg-lighter rounded-md p-1">
          <button
            className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all
                      ${activeCategory === 'draw' ? 'bg-google-blue/10 text-google-blue' : 'text-google-grey-200 hover:text-google-grey-100'}`}
            onClick={() => setActiveCategory('draw')}
          >
            Draw
          </button>
          <button
            className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all
                      ${activeCategory === 'measure' ? 'bg-google-blue/10 text-google-blue' : 'text-google-grey-200 hover:text-google-grey-100'}`}
            onClick={() => setActiveCategory('measure')}
          >
            Measure
          </button>
          <button
            className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all
                      ${activeCategory === 'edit' ? 'bg-google-blue/10 text-google-blue' : 'text-google-grey-200 hover:text-google-grey-100'}`}
            onClick={() => setActiveCategory('edit')}
          >
            Edit
          </button>
        </div>
        
        {/* Draw category */}
        {activeCategory === 'draw' && (
          <div className="space-y-2">
            <div className="grid grid-cols-4 gap-2">
              <button
                className={getButtonStyle('point', DRAW_MODES.POINT)}
                onClick={() => setMode(DRAW_MODES.POINT)}
                onMouseEnter={(e) => handleMouseEnter('Add Point', e)}
                onMouseLeave={handleMouseLeave}
                title="Add Point"
              >
                <Pencil size={18} />
              </button>
              <button
                className={getButtonStyle('line', DRAW_MODES.LINE)}
                onClick={() => setMode(DRAW_MODES.LINE)}
                onMouseEnter={(e) => handleMouseEnter('Draw Line', e)}
                onMouseLeave={handleMouseLeave}
                title="Draw Line"
              >
                <Ruler size={18} />
              </button>
              <button
                className={getButtonStyle('polygon', DRAW_MODES.POLYGON)}
                onClick={() => setMode(DRAW_MODES.POLYGON)}
                onMouseEnter={(e) => handleMouseEnter('Draw Polygon', e)}
                onMouseLeave={handleMouseLeave}
                title="Draw Polygon"
              >
                <Hexagon size={18} />
              </button>
              <button
                className={getButtonStyle('rectangle', DRAW_MODES.RECTANGLE)}
                onClick={() => setMode(DRAW_MODES.RECTANGLE)}
                onMouseEnter={(e) => handleMouseEnter('Draw Rectangle', e)}
                onMouseLeave={handleMouseLeave}
                title="Draw Rectangle"
              >
                <Square size={18} />
              </button>
            </div>
            <div className="grid grid-cols-4 gap-2">
              <button
                className={getButtonStyle('circle', DRAW_MODES.CIRCLE)}
                onClick={() => setMode(DRAW_MODES.CIRCLE)}
                onMouseEnter={(e) => handleMouseEnter('Draw Circle', e)}
                onMouseLeave={handleMouseLeave}
                title="Draw Circle"
              >
                <Circle size={18} />
              </button>
              <button
                className={getButtonStyle('select', DRAW_MODES.SELECT)}
                onClick={() => setMode(DRAW_MODES.SELECT)}
                onMouseEnter={(e) => handleMouseEnter('Select Features', e)}
                onMouseLeave={handleMouseLeave}
                title="Select Features"
              >
                <MousePointer size={18} />
              </button>
              <button
                className={getButtonStyle('cancel')}
                onClick={handleCancel}
                disabled={!isDrawing && pointsRef.current.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Cancel Drawing', e)}
                onMouseLeave={handleMouseLeave}
                title="Cancel Drawing"
              >
                <RotateCcw size={18} />
              </button>
              <button
                className={getButtonStyle('undo')}
                onClick={handleUndo}
                disabled={drawHistory.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Undo Last Action', e)}
                onMouseLeave={handleMouseLeave}
                title="Undo Last Action"
              >
                <Undo2 size={18} />
              </button>
            </div>
          </div>
        )}
        
        {/* Measure category */}
        {activeCategory === 'measure' && (
          <div className="space-y-2">
            <div className="grid grid-cols-3 gap-2">
              <button
                className={getButtonStyle('measure', DRAW_MODES.MEASURE)}
                onClick={() => setMode(DRAW_MODES.MEASURE)}
                onMouseEnter={(e) => handleMouseEnter('Measure Distance', e)}
                onMouseLeave={handleMouseLeave}
                title="Measure Distance"
              >
                <Ruler size={18} />
              </button>
              <button
                className={getButtonStyle('cancel')}
                onClick={handleCancel}
                disabled={!isDrawing && pointsRef.current.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Cancel Measurement', e)}
                onMouseLeave={handleMouseLeave}
                title="Cancel Measurement"
              >
                <RotateCcw size={18} />
              </button>
              <button
                className={getButtonStyle('clear')}
                onClick={handleClearAll}
                disabled={currentFeatures.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Clear All Measurements', e)}
                onMouseLeave={handleMouseLeave}
                title="Clear All Measurements"
              >
                <Trash2 size={18} />
              </button>
            </div>
          </div>
        )}
        
        {/* Edit category */}
        {activeCategory === 'edit' && (
          <div className="space-y-2">
            <div className="grid grid-cols-4 gap-2">
              <button
                className={getButtonStyle('clear')}
                onClick={handleClearAll}
                disabled={currentFeatures.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Clear All', e)}
                onMouseLeave={handleMouseLeave}
                title="Clear All"
              >
                <Trash2 size={18} />
              </button>
              <button
                className={getButtonStyle('export')}
                onClick={handleExport}
                disabled={currentFeatures.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Export as GeoJSON', e)}
                onMouseLeave={handleMouseLeave}
                title="Export as GeoJSON"
              >
                <Download size={18} />
              </button>
              <button
                className={getButtonStyle('info')}
                onClick={() => showNotification('Feature count: ' + currentFeatures.length, 'info')}
                disabled={currentFeatures.length === 0}
                onMouseEnter={(e) => handleMouseEnter('Feature Info', e)}
                onMouseLeave={handleMouseLeave}
                title="Feature Info"
              >
                <Info size={18} />
              </button>
              <button
                className={getButtonStyle('move')}
                disabled={true}
                onMouseEnter={(e) => handleMouseEnter('Move Features (Coming Soon)', e)}
                onMouseLeave={handleMouseLeave}
                title="Move Features (Coming Soon)"
              >
                <Move size={18} />
              </button>
            </div>
          </div>
        )}
        
        {/* Tooltip */}
        {showTooltip && (
          <div 
            className="absolute bg-google-bg-light text-google-grey-100 py-1 px-2 text-xs rounded shadow-md pointer-events-none z-10 transform -translate-y-full -translate-x-1/2 whitespace-nowrap"
            style={{ 
              left: `${tooltipPosition.x}px`, 
              top: `${tooltipPosition.y}px`
            }}
          >
            {tooltipText}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="drawing-tools-control" style={{ position: 'absolute', top: '215px', left: '5px', zIndex: 11 }}>
      <div className="relative">
        {/* Main toggle button - always visible */}
        <button 
          className={`w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all
                    ${isExpanded ? 'bg-google-blue text-white rotate-45' : 'bg-google-bg text-google-blue hover:bg-google-bg-light'}`}
          onClick={toggleExpanded}
          aria-label={isExpanded ? "Close drawing tools" : "Open drawing tools"}
        >
          <PencilRuler size={20} />
        </button>
        
        {/* Expanded panel */}
        {isExpanded && (
          <div className="absolute bottom-14 left-0 animate-scale-in">
            {renderToolbar()}
          </div>
        )}
      </div>
      
      {/* Measurement info popup */}
      {measurementInfo && (
        <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-8 bg-google-bg-light text-google-grey-100 px-3 py-2 rounded-lg shadow-lg text-sm z-50">
          <span className="font-medium">{measurementInfo.distance.toFixed(2)} km</span>
        </div>
      )}
      
      {/* Drawing instruction */}
      {instructionText && (
        <div className="fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-google-bg-light/90 text-google-grey-100 px-4 py-2 rounded-lg shadow-lg text-sm z-50 max-w-sm text-center">
          {instructionText}
        </div>
      )}
    </div>
  );
};

export default DrawingTools;