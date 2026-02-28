// src/components/Tutorial/TutorialPopup.jsx
import { useEffect, useState } from 'react';
import { X, ArrowRight, ArrowLeft, Info } from 'lucide-react';
import '../../styles/tutorialPopup.css';

const TutorialPopup = ({ 
  title, 
  content, 
  position, 
  target, 
  onComplete, 
  onSkip,
  onPrevious,
  hasPrevious,
  hasNext,
  step,
  totalSteps
}) => {
  const [popupStyle, setPopupStyle] = useState({});
  const [arrowStyle, setArrowStyle] = useState({});
  
  useEffect(() => {
    try {
      if (target) {
        // Find target element position
        const targetElement = document.querySelector(target);
        if (targetElement) {
          const rect = targetElement.getBoundingClientRect();
          const popupWidth = 350; // Increased width for better readability
          const popupHeight = 180; // Adjusted height
          
          // Calculate position based on specified position
          let top, left, arrowPos;
          
          switch(position) {
            case 'top':
              top = rect.top - popupHeight - 15; // More space
              left = rect.left + (rect.width / 2) - (popupWidth / 2);
              arrowPos = { bottom: '-8px', left: '50%', transform: 'translateX(-50%)' };
              break;
            case 'bottom':
              top = rect.bottom + 15; // More space
              left = rect.left + (rect.width / 2) - (popupWidth / 2);
              arrowPos = { top: '-8px', left: '50%', transform: 'translateX(-50%)' };
              break;
            case 'left':
              top = rect.top + (rect.height / 2) - (popupHeight / 2);
              left = rect.left - popupWidth - 15; // More space
              arrowPos = { right: '-8px', top: '50%', transform: 'translateY(-50%)' };
              break;
            case 'right':
              top = rect.top + (rect.height / 2) - (popupHeight / 2);
              left = rect.right + 15; // More space
              arrowPos = { left: '-8px', top: '50%', transform: 'translateY(-50%)' };
              break;
            case 'center':
              // Center in viewport
              top = (window.innerHeight - popupHeight) / 2;
              left = (window.innerWidth - popupWidth) / 2;
              arrowPos = { display: 'none' }; // No arrow for centered popups
              break;
            default:
              top = rect.bottom + 15;
              left = rect.left + (rect.width / 2) - (popupWidth / 2);
              arrowPos = { top: '-8px', left: '50%', transform: 'translateX(-50%)' };
          }
          
          // Ensure popup stays in viewport with better padding
          const padding = 20; // Increased padding
          if (left < padding) left = padding;
          if (left + popupWidth > window.innerWidth - padding) 
            left = window.innerWidth - popupWidth - padding;
          if (top < padding) top = padding;
          if (top + popupHeight > window.innerHeight - padding) 
            top = window.innerHeight - popupHeight - padding;
          
          setPopupStyle({
            top: `${top}px`,
            left: `${left}px`,
            width: `${popupWidth}px`,
          });
          
          setArrowStyle(arrowPos);
        }
      } else if (position === 'center') {
        // Handle center position without specific target
        const popupWidth = 350; // Increased width
        const popupHeight = 180; // Adjusted height
        const top = (window.innerHeight - popupHeight) / 2;
        const left = (window.innerWidth - popupWidth) / 2;
        
        setPopupStyle({
          top: `${top}px`,
          left: `${left}px`,
          width: `${popupWidth}px`,
        });
        
        setArrowStyle({ display: 'none' });
      }
    } catch (error) {
      console.error("Error positioning tutorial popup:", error);
      
      // Fallback to center position if there's an error
      const popupWidth = 350;
      const popupHeight = 180;
      setPopupStyle({
        top: `${(window.innerHeight - popupHeight) / 2}px`,
        left: `${(window.innerWidth - popupWidth) / 2}px`,
        width: `${popupWidth}px`,
      });
      setArrowStyle({ display: 'none' });
    }
  }, [target, position]);
  
  // Handle button clicks
  const handleCompleteClick = () => {
    console.log("Next/Complete button clicked");
    if (onComplete) {
      onComplete();
    }
  };
  
  const handlePreviousClick = () => {
    console.log("Previous button clicked");
    if (onPrevious) {
      onPrevious();
    }
  };
  
  const handleSkipClick = () => {
    console.log("Skip button clicked");
    if (onSkip) {
      onSkip();
    }
  };
  
  return (
    <div className="tutorial-overlay">
      <div className="tutorial-popup" style={popupStyle}>
        <div className="tutorial-arrow" style={arrowStyle}></div>
        <div className="tutorial-header">
          <div className="tutorial-title">
            <Info size={16} className="tutorial-icon" />
            <h3>{title}</h3>
          </div>
          <button className="tutorial-close-btn" onClick={handleSkipClick}>
            <X size={16} />
          </button>
        </div>
        <div className="tutorial-content">
          {content}
        </div>
        <div className="tutorial-footer">
          <div className="tutorial-progress">
            {step} of {totalSteps}
          </div>
          <div className="tutorial-actions">
            {hasPrevious && (
              <button className="tutorial-prev-btn" onClick={handlePreviousClick}>
                <ArrowLeft size={16} />
                <span>Previous</span>
              </button>
            )}
            <button className="tutorial-next-btn" onClick={handleCompleteClick}>
              <span>{hasNext ? 'Next' : 'Got it'}</span>
              {hasNext && <ArrowRight size={16} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TutorialPopup;