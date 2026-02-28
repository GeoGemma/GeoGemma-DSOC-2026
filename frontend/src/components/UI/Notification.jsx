// src/components/UI/Notification.jsx
import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { AlertCircle, CheckCircle, InfoIcon, XCircle, X } from 'lucide-react';
import '../../styles/notification.css';

const Notification = ({ message, type = 'info', duration = 3000, onClose }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [progress, setProgress] = useState(100);
  const [intervalId, setIntervalId] = useState(null);

  useEffect(() => {
    // Show notification with entrance animation
    setIsVisible(true);
    
    // Start progress timer
    const steps = 100;
    const stepDuration = duration / steps;
    
    const id = setInterval(() => {
      setProgress(prev => {
        if (prev <= 0) {
          clearInterval(id);
          setIsVisible(false);
          return 0;
        }
        return prev - (100 / steps);
      });
    }, stepDuration);
    
    setIntervalId(id);

    // Auto-hide after duration
    const hideTimer = setTimeout(() => {
      setIsVisible(false);
      if (onClose) onClose();
    }, duration);

    return () => {
      clearTimeout(hideTimer);
      clearInterval(id);
    };
  }, [duration, message, onClose]);

  const handleClose = () => {
    if (intervalId) clearInterval(intervalId);
    setIsVisible(false);
    if (onClose) onClose();
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle size={18} />;
      case 'error':
        return <XCircle size={18} />;
      case 'warning':
        return <AlertCircle size={18} />;
      case 'info':
      default:
        return <InfoIcon size={18} />;
    }
  };

  if (!isVisible) return null;

  return (
    <div className={`notification notification-${type} slide-up`}>
      <div className="notification-icon">
        {getIcon()}
      </div>
      <div className="notification-content">
        {message}
      </div>
      <button className="notification-close" onClick={handleClose}>
        <X size={16} />
      </button>
      <div 
        className="notification-progress" 
        style={{ width: `${progress}%` }} 
      />
    </div>
  );
};

Notification.propTypes = {
  message: PropTypes.string.isRequired,
  type: PropTypes.oneOf(['info', 'success', 'warning', 'error']),
  duration: PropTypes.number,
  onClose: PropTypes.func
};

export default Notification;