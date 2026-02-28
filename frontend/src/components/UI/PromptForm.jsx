// src/components/UI/PromptForm.jsx
import { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Search, Mic, X, Send, Clock } from 'lucide-react';
import { useMap } from '../../contexts/MapContext';
import { geocodeLocation, analyzePrompt } from '../../services/api';
import { generateLayerId } from '../../utils/mapUtils';
import { useAuth } from '../../contexts/AuthContext';
import LoginPopup from './LoginPopup';
import '../../styles/promptForm.css';

const PromptForm = ({ showNotification, showLoading, hideLoading }) => {
  const [prompt, setPrompt] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const promptRef = useRef(null);
  const inputRef = useRef(null);
  const justSubmittedRef = useRef(false);
  const recognitionRef = useRef(null);
  const { addLayer, addMarker, flyToLocation, clearMarkers } = useMap();
  const { currentUser, loading } = useAuth();

  const examplePromptCategories = [
    {
      name: "Popular",
      prompts: [
        "Show NDVI vegetation in Paris for 2023",
        "Land surface temperature in Dubai during summer 2022", 
        "Surface water change in Lake Mead since 2000"
      ]
    },
    {
      name: "You might like",
      prompts: [
        "Urban growth in Shanghai between 2015-2023",
        "Detect burned areas in California after 2021 wildfires"
      ]
    }
  ];

  const recentSearches = [
    "NDVI Manila 2025",
    "Surface water in Venice"
  ];

  // Initialize speech recognition
  useEffect(() => {
    // Check if the browser supports SpeechRecognition
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';
      
      // Set up event handlers
      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setPrompt(transcript);
        setIsListening(false);
        // Focus on input after speech recognition
        if (inputRef.current) {
          inputRef.current.focus();
        }
      };
      
      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        showNotification('Speech recognition failed. Please try again.', 'error');
      };
      
      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
    
    return () => {
      // Clean up
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
    };
  }, [showNotification]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (promptRef.current && !promptRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (!loading) {
      if (currentUser === null) {
        setShowLoginPopup(true);
      } else {
        setShowLoginPopup(false);
      }
    }
  }, [currentUser, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!prompt.trim()) {
      showNotification('Please enter a prompt', 'warning');
      return;
    }

    if (!currentUser) {
      setShowLoginPopup(true);
      return;
    }

    justSubmittedRef.current = true;
    setShowSuggestions(false);
    if (inputRef.current) inputRef.current.blur();

    showLoading('Processing your request...');

    try {
      // Dispatch event to update chat history with user's prompt
      const promptEvent = new CustomEvent('prompt-submitted', {
        detail: { prompt, response: null }
      });
      window.dispatchEvent(promptEvent);

      clearMarkers();

      const result = await analyzePrompt(prompt, currentUser?.uid);
      console.log('API response:', result);

      let responseText = '';

      if (result && result.success && result.data) {
        const { location, processing_type, tile_url, latitude, longitude, metadata } = result.data;

        if (tile_url) {
          const layerId = generateLayerId(location, processing_type || prompt);
          const newLayer = {
            id: layerId,
            tile_url,
            location,
            processing_type: processing_type || prompt,
            latitude: latitude || null,
            longitude: longitude || null,
            opacity: 0.8,
            visibility: 'visible',
            metadata
          };
          addLayer(newLayer);

          if (location && location.trim() !== '') {
            if (latitude && longitude) {
              const lat = parseFloat(latitude);
              const lon = parseFloat(longitude);
              if (!isNaN(lat) && !isNaN(lon)) {
                addMarker(lat, lon);
                flyToLocation(location, lat, lon);
              }
            } else {
              try {
                const geocodeResult = await geocodeLocation(location);
                if (geocodeResult) {
                  addMarker(geocodeResult.lat, geocodeResult.lon);
                  flyToLocation(location, geocodeResult.lat, geocodeResult.lon);
                }
              } catch (geocodeError) {
                console.error('Geocoding error:', geocodeError);
              }
            }
          }

          responseText = `I've added ${processing_type || 'imagery'} layer for ${location}. `;
          if (metadata) {
            if (metadata.STATUS === 'Metadata Processed Successfully' || metadata.Status === 'Metadata Processed Successfully') {
              if (metadata.IMAGE_DATE || metadata['IMAGE DATE']) {
                responseText += `Image date: ${metadata.IMAGE_DATE || metadata['IMAGE DATE']}. `;
              }
              if (metadata.SOURCE_DATASET || metadata['SOURCE DATASET']) {
                responseText += `Source: ${metadata.SOURCE_DATASET || metadata['SOURCE DATASET']}. `;
              }
              const statsKey = Object.keys(metadata).find(key => key.includes('STATS'));
              if (statsKey && typeof metadata[statsKey] === 'object') {
                const stats = metadata[statsKey];
                if (stats.Mean) responseText += `Average value: ${stats.Mean}. `;
              }
            }
            responseText += "You can see it on the map now and check the Info panel for more details.";
          } else {
            responseText += "You can see it on the map now.";
          }

          showNotification(`Added layer: ${location} (${processing_type || prompt})`, 'success');
        } else {
          responseText = "I couldn't generate a visualization for this request.";
          showNotification('Error: No visualization data available', 'error');
        }
      } else {
        responseText = result?.message || "No imagery available for this request.";
        showNotification(responseText, 'error');
      }

      // Dispatch event to update chat history with response
      window.dispatchEvent(new CustomEvent('prompt-submitted', {
        detail: { prompt: null, response: responseText }
      }));

      setPrompt('');
    } catch (error) {
      console.error('Error processing prompt:', error);
      let errorMessage = 'There was a problem processing your request';
      if (error.response) {
        errorMessage += `: ${error.response.data?.message || error.response.statusText}`;
      } else if (error.request) {
        errorMessage += ': No response from server.';
      } else {
        errorMessage += `: ${error.message}`;
      }

      window.dispatchEvent(new CustomEvent('prompt-submitted', {
        detail: { prompt: null, response: errorMessage }
      }));
      showNotification(errorMessage, 'error');
    } finally {
      hideLoading();
      setShowSuggestions(false);
    }
  };

  const handleInputFocus = () => {
    if (justSubmittedRef.current) {
      justSubmittedRef.current = false;
      return;
    }
    setIsFocused(true);
    setShowSuggestions(true);
  };

  const handleClearPrompt = () => {
    setPrompt('');
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setPrompt(suggestion);
    setShowSuggestions(false);
    setTimeout(() => {
      if (promptRef.current) {
        const form = promptRef.current.querySelector('form');
        if (form) form.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    }, 100);
  };

  const toggleSpeechRecognition = () => {
    if (!recognitionRef.current) {
      showNotification('Speech recognition is not supported in your browser', 'error');
      return;
    }

    if (isListening) {
      // Stop listening
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.error("Error stopping speech recognition:", e);
      }
      setIsListening(false);
      showNotification('Voice input stopped', 'info');
    } else {
      // Start listening
      try {
        recognitionRef.current.start();
        setIsListening(true);
        showNotification('Listening... Speak now', 'info');
      } catch (error) {
        console.error('Speech recognition error:', error);
        showNotification('Could not start speech recognition', 'error');
        setIsListening(false);
      }
    }
  };

  return (
    <>
      <div className={`prompt-container ${isFocused ? 'focused' : ''}`} ref={promptRef}>
        <form className="prompt-form" onSubmit={handleSubmit}>
          <div className="prompt-icon"><Search size={18} /></div>
          <input
            ref={inputRef}
            type="text"
            className="prompt-input"
            placeholder="Search for Earth imagery..."
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              setShowSuggestions(true); // Reopen suggestions on typing
            }}
            onFocus={handleInputFocus}
          />
          {prompt && (
            <button 
              type="button" 
              className="prompt-clear" 
              onClick={handleClearPrompt} 
              title="Clear input"
            >
              <X size={16} />
            </button>
          )}
          <button 
            type="button" 
            className={`prompt-voice ${isListening ? 'listening' : ''}`} 
            onClick={toggleSpeechRecognition} 
            title={isListening ? "Stop listening" : "Voice search"}
          >
            <Mic size={18} />
          </button>
          <button type="submit" className="prompt-submit" title="Search">
            <Send size={16} />
          </button>
        </form>
    
        {showSuggestions && (
          <div className="prompt-suggestions scale-in">
            {recentSearches.length > 0 && (
              <div className="suggestion-section">
                <div className="suggestion-header">RECENT SEARCHES</div>
                <div className="grid-suggestions">
                  {recentSearches.map((item, index) => (
                    <div key={`recent-${index}`} className="suggestion-item" onClick={() => handleSuggestionClick(item)}>
                      <Clock size={16} className="suggestion-icon" />
                      <span className="suggestion-text">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {examplePromptCategories.map((category, catIndex) => (
              <div className="suggestion-section" key={`category-${catIndex}`}>
                <div className="suggestion-header">{category.name.toUpperCase()}</div>
                <div className="grid-suggestions">
                  {category.prompts.map((item, index) => (
                    <div key={`example-${category.name}-${index}`} className="suggestion-item" onClick={() => handleSuggestionClick(item)}>
                      <Search size={16} className="suggestion-icon" />
                      <span className="suggestion-text">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {showLoginPopup && !loading && (
        <LoginPopup onClose={() => setShowLoginPopup(false)} />
      )}
    </>
  );
};

PromptForm.propTypes = {
  showNotification: PropTypes.func.isRequired,
  showLoading: PropTypes.func.isRequired,
  hideLoading: PropTypes.func.isRequired
};

export default PromptForm;