// src/components/Map/AppMap.jsx
import { useEffect, useRef } from 'react';
import { useMap } from '../../contexts/MapContext';
import 'maplibre-gl/dist/maplibre-gl.css';
import '../../styles/map.css';
import '../../styles/topbar.css';

const AppMap = () => {
  const mapContainer = useRef(null);
  const { initializeMap } = useMap();

  useEffect(() => {
    if (mapContainer.current) {
      initializeMap(mapContainer.current);
    }
  }, [initializeMap]);

  return (
    <div ref={mapContainer} className="map-container w-full main-content absolute" />
  );
};

export default AppMap;