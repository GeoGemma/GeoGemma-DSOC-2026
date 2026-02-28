// src/hooks/useMeasurement.js
import { useState, useEffect, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import * as turf from '@turf/turf';
import { useMap } from '../contexts/MapContext';

const useMeasurement = (showNotification) => {
  const { map } = useMap();
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [markers, setMarkers] = useState([]);
  const [line, setLine] = useState(null);
  const [distance, setDistance] = useState(0);
  const [popup, setPopup] = useState(null);
  
  // Clean up measurement elements
  const resetMeasurement = useCallback(() => {
    // Remove markers
    markers.forEach(marker => marker.remove());
    setMarkers([]);
    
    // Remove line
    if (line && map.getSource('measure-line')) {
      map.removeLayer('measure-line-layer');
      map.removeSource('measure-line');
      setLine(null);
    }
    
    // Remove popup
    if (popup) {
      popup.remove();
      setPopup(null);
    }
    
    setDistance(0);
  }, [map, markers, line, popup]);
  
  // Update the line on map
  const updateLine = useCallback((points) => {
    if (!map || points.length < 2) return;
    
    const geojson = {
      'type': 'Feature',
      'geometry': {
        'type': 'LineString',
        'coordinates': points
      }
    };
    
    if (map.getSource('measure-line')) {
      map.getSource('measure-line').setData(geojson);
    } else {
      map.addSource('measure-line', {
        'type': 'geojson',
        'data': geojson
      });
      
      map.addLayer({
        'id': 'measure-line-layer',
        'type': 'line',
        'source': 'measure-line',
        'paint': {
          'line-color': '#FF0000',
          'line-width': 2,
          'line-dasharray': [2, 1]
        }
      });
    }
    
    setLine(geojson);
  }, [map]);
  
  // Update distance display
  const updateDistanceDisplay = useCallback((points, lastPoint) => {
    if (!map || points.length < 2) return;
    
    // Calculate total distance
    let totalDistance = 0;
    for (let i = 1; i < points.length; i++) {
      const from = turf.point(points[i - 1]);
      const to = turf.point(points[i]);
      totalDistance += turf.distance(from, to, {units: 'kilometers'});
    }
    
    setDistance(totalDistance);
    
    // Update or create popup
    if (!popup) {
      const newPopup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false
      });
      setPopup(newPopup);
    }
    
    popup?.setLngLat(lastPoint)
      .setHTML(`<strong>Distance:</strong> ${totalDistance.toFixed(2)} km`)
      .addTo(map);
  }, [map, popup]);
  
  // Start measuring
  const startMeasuring = useCallback(() => {
    if (!map) return;
    
    resetMeasurement();
    setIsMeasuring(true);
    map.getCanvas().style.cursor = 'crosshair';
    
    showNotification('Click on the map to start measuring. Double-click to finish.', 'info');
  }, [map, resetMeasurement, showNotification]);
  
  // Stop measuring
  const stopMeasuring = useCallback(() => {
    if (!map) return;
    
    setIsMeasuring(false);
    map.getCanvas().style.cursor = '';
    
    if (distance > 0) {
      showNotification(`Measured distance: ${distance.toFixed(2)} km`, 'success');
    }
  }, [map, distance, showNotification]);
  
  // Add click handler
  const handleMapClick = useCallback((e) => {
    if (!isMeasuring || !map) return;
    
    const point = [e.lngLat.lng, e.lngLat.lat];
    
    // Add marker
    const marker = new maplibregl.Marker({
      color: '#FF0000',
      draggable: false
    }).setLngLat(point).addTo(map);
    
    setMarkers(prev => [...prev, marker]);
    
    // Get all points
    const points = [...markers, marker].map(m => m.getLngLat().toArray());
    
    // Update line and distance display
    updateLine(points);
    updateDistanceDisplay(points, point);
  }, [isMeasuring, map, markers, updateLine, updateDistanceDisplay]);
  
  // Add mouse move handler for live measurement preview
  const handleMouseMove = useCallback((e) => {
    if (!isMeasuring || markers.length === 0 || !map) return;
    
    const currentPoints = markers.map(marker => marker.getLngLat().toArray());
    const mousePoint = [e.lngLat.lng, e.lngLat.lat];
    const allPoints = [...currentPoints, mousePoint];
    
    updateLine(allPoints);
    updateDistanceDisplay(allPoints, mousePoint);
  }, [isMeasuring, markers, map, updateLine, updateDistanceDisplay]);
  
  // Handle double click to finish measurement
  const handleDblClick = useCallback((e) => {
    if (!isMeasuring || !map) return;
    
    e.preventDefault(); // Prevent regular click from being triggered
    stopMeasuring();
  }, [isMeasuring, map, stopMeasuring]);
  
  // Set up and clean up event listeners
  useEffect(() => {
    if (!map) return;
    
    if (isMeasuring) {
      map.on('click', handleMapClick);
      map.on('mousemove', handleMouseMove);
      map.on('dblclick', handleDblClick);
    } else {
      map.off('click', handleMapClick);
      map.off('mousemove', handleMouseMove);
      map.off('dblclick', handleDblClick);
    }
    
    return () => {
      map.off('click', handleMapClick);
      map.off('mousemove', handleMouseMove);
      map.off('dblclick', handleDblClick);
    };
  }, [map, isMeasuring, handleMapClick, handleMouseMove, handleDblClick]);
  
  return {
    isMeasuring,
    startMeasuring,
    stopMeasuring,
    resetMeasurement,
    distance
  };
};

export default useMeasurement;