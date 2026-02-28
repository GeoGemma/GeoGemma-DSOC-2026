// src/components/Map/MeasureToolControl.jsx
import { useEffect } from 'react';
import PropTypes from 'prop-types';
import useMeasurement from '../../hooks/useMeasurement';

const MeasureToolControl = ({ showNotification }) => {
  const {
    isMeasuring,
    startMeasuring,
    stopMeasuring
  } = useMeasurement(showNotification);

  const toggleMeasurement = () => {
    if (isMeasuring) {
      stopMeasuring();
    } else {
      startMeasuring();
    }
  };

  return (
    <div className="flex flex-col gap-2 p-2">
      <button
        className={`px-3 py-2 rounded bg-background-sidebar hover:bg-primary/50 
                   flex items-center gap-2 text-sm ${isMeasuring ? 'bg-primary/80' : ''}`}
        onClick={toggleMeasurement}
      >
        {isMeasuring ? 'Stop Measuring' : 'Start Measuring'}
      </button>
      
      {isMeasuring && (
        <div className="text-xs bg-black/30 p-2 rounded">
          Click on the map to add points. Double-click to finish.
        </div>
      )}
    </div>
  );
};

MeasureToolControl.propTypes = {
  showNotification: PropTypes.func.isRequired
};

export default MeasureToolControl;