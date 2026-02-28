// src/components/Map/BasemapControl.jsx
import { useState } from 'react';
import { Globe, Grid } from 'lucide-react';
import { useMap } from '../../contexts/MapContext';
import '../../styles/BasemapControl.css';

const BasemapControl = () => {
  const { currentBasemap, setBasemap } = useMap();
  const [isOpen, setIsOpen] = useState(false);
  
  const basemapOptions = [
    { id: 'dark', name: 'Dark', icon: <Grid size={16} /> },
    { id: 'satellite', name: 'Satellite', icon: <Globe size={16} /> }
  ];
  
  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };
  
  const handleBasemapChange = (basemapId) => {
    setBasemap(basemapId);
    setIsOpen(false);
  };
  
  return (
    <div className="basemap-control">
      <button 
        className="basemap-toggle-button"
        onClick={toggleDropdown}
        title="Change basemap"
      >
        {currentBasemap === 'satellite' ? <Grid size={20} /> : <Globe size={20} />}
      </button>
      
      {isOpen && (
        <div className="basemap-dropdown">
          {basemapOptions.map(option => (
            <button
              key={option.id}
              className={`basemap-option ${currentBasemap === option.id ? 'active' : ''}`}
              onClick={() => handleBasemapChange(option.id)}
            >
              <span className="basemap-icon">{option.icon}</span>
              <span className="basemap-name">{option.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default BasemapControl;