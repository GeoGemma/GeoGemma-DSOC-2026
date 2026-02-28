// src/services/api.js
import axios from 'axios';

// Get base URL from environment variable or default to the deployed backend
const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'https://geogemma-backend-312711753493.us-central1.run.app';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false // Disable credentials when using '*' for CORS
});

// Handle API errors consistently
const handleApiError = (error) => {
  console.error('API Error:', error);
  
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    return {
      success: false,
      message: error.response.data.message || 'Server error',
      status: error.response.status
    };
  } else if (error.request) {
    // The request was made but no response was received
    return {
      success: false,
      message: 'No response from server. Please check your connection.',
      status: 0
    };
  } else {
    // Something happened in setting up the request that triggered an Error
    return {
      success: false,
      message: error.message || 'Unknown error',
      status: 0
    };
  }
};

// API functions
export const analyzePrompt = async (prompt, userId = null) => {
  try {
    console.log(`Analyzing prompt with user ID: ${userId}`);
    
    // First try with axios
    const response = await api.post('/api/analyze', {
      prompt,
      save_result: !!userId, // Only save if user is authenticated
      user_id: userId
    });
    
    // If the analysis was successful and user is authenticated, save the layer
    if (response.data.success && userId && response.data.data && response.data.data.tile_url) {
      try {
        // Save the layer to the user's account
        const layerId = `layer_${Date.now()}`;
        await saveMapLayer(userId, layerId, {
          id: layerId,
          tile_url: response.data.data.tile_url,
          location: response.data.data.location,
          processing_type: response.data.data.processing_type,
          timestamp: Date.now(),
          metadata: response.data.data.metadata || null
        });
        console.log(`Layer saved for user ${userId}`);
      } catch (saveError) {
        console.error('Error saving layer:', saveError);
        // Don't fail the overall request if saving fails
      }
    }
    
    return response.data;
  } catch (axiosError) {
    console.error('Failed with axios, trying with fetch:', axiosError);
    
    // If axios fails, try with direct fetch as fallback
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          prompt,
          save_result: !!userId,
          user_id: userId
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // If the analysis was successful and user is authenticated, save the layer
      if (data.success && userId && data.data && data.data.tile_url) {
        try {
          // Save the layer to the user's account
          const layerId = `layer_${Date.now()}`;
          await saveMapLayer(userId, layerId, {
            id: layerId,
            tile_url: data.data.tile_url,
            location: data.data.location,
            processing_type: data.data.processing_type,
            timestamp: Date.now(),
            metadata: data.data.metadata || null
          });
          console.log(`Layer saved for user ${userId}`);
        } catch (saveError) {
          console.error('Error saving layer:', saveError);
          // Don't fail the overall request if saving fails
        }
      }
      
      return data;
    } catch (fetchError) {
      console.error('Fetch fallback also failed:', fetchError);
      return handleApiError(fetchError);
    }
  }
};

export const getLayers = async () => {
  try {
    const response = await api.get('/api/layers');
    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getSavedLayers = async (userId = null, limit = 20, skip = 0) => {
  try {
    const params = { limit, skip };
    if (userId) params.user_id = userId;
    
    const response = await api.get('/api/saved-layers', { params });
    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getAnalyses = async (userId = null, limit = 20, skip = 0) => {
  try {
    const params = { limit, skip };
    if (userId) params.user_id = userId;
    
    const response = await api.get('/api/analyses', { params });
    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    return handleApiError(error);
  }
};

export const deleteLayer = async (layerId) => {
  try {
    const response = await api.delete(`/api/layers/${layerId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
};

export const clearLayers = async () => {
  try {
    const response = await api.post('/api/layers/clear');
    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
};

export const createTimeSeriesAnalysis = async (data, userId = null) => {
  try {
    // Include user ID if available
    const requestData = {
      ...data,
      user_id: userId
    };
    
    const response = await api.post('/api/time-series', requestData);
    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
};

export const createComparisonAnalysis = async (data, userId = null) => {
  try {
    // Include user ID if available
    const requestData = {
      ...data,
      user_id: userId
    };
    
    const response = await api.post('/api/comparison', requestData);
    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
};

export const geocodeLocation = async (location) => {
  try {
    // Use a free geocoding service like Nominatim instead of Google Maps
    const response = await axios.get(`https://nominatim.openstreetmap.org/search`, {
      params: {
        q: location,
        format: 'json',
        limit: 1
      },
      headers: {
        'User-Agent': 'GeoGemma Application'
      }
    });
    
    if (response.data && response.data.length > 0) {
      const result = response.data[0];
      return {
        lat: parseFloat(result.lat),
        lon: parseFloat(result.lon),
        display_name: result.display_name
      };
    }
    
    return null;
  } catch (error) {
    console.error('Geocoding error:', error);
    return null;
  }
};

export const exportMap = async (layerId, format = 'png') => {
  try {
    const response = await api.get(`/api/export/${layerId}`, {
      params: { format },
      responseType: 'blob'
    });
    
    // Create a download link for the blob
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `map-export-${layerId}.${format}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    
    return {
      success: true,
      message: 'Export successful'
    };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getSystemHealth = async () => {
  try {
    const response = await api.get('/health');
    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    return handleApiError(error);
  }
};

export default api;
// --- Firestore-backed API functions ---

// User Profile
export const getUserProfile = async (userId) => {
  try {
    const response = await api.get(`/api/user-profile/${userId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const createUserProfile = async (userId, profile) => {
  try {
    const response = await api.post('/api/user-profile', { user_id: userId, profile });
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const updateUserProfile = async (userId, updates) => {
  try {
    const response = await api.patch(`/api/user-profile/${userId}`, updates);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

// Map Layers (Firestore)
export const saveMapLayer = async (userId, layerId, layer) => {
  try {
    const response = await api.post('/api/layers', { user_id: userId, layer_id: layerId, layer });
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getMapLayers = async (userId) => {
  try {
    const response = await api.get(`/api/layers/${userId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const deleteMapLayer = async (userId, layerId) => {
  try {
    const response = await api.delete(`/api/layers/${userId}/${layerId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const clearUserLayers = async (userId) => {
  try {
    const response = await api.delete(`/api/layers/${userId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

// Analyses (Firestore)
export const saveAnalysis = async (userId, analysisId, analysis) => {
  try {
    const response = await api.post('/api/analyses', { user_id: userId, analysis_id: analysisId, analysis });
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getAnalysesFirestore = async (userId) => {
  try {
    const response = await api.get(`/api/analyses/${userId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

// Chat History
export const saveChatMessage = async (userId, messageId, message) => {
  try {
    const response = await api.post('/api/chat-history', { user_id: userId, message_id: messageId, message });
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getChatHistory = async (userId) => {
  try {
    const response = await api.get(`/api/chat-history/${userId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

// Custom Areas
export const saveCustomArea = async (userId, areaId, area) => {
  try {
    const response = await api.post('/api/custom-areas', { user_id: userId, area_id: areaId, area });
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

export const getCustomAreas = async (userId) => {
  try {
    const response = await api.get(`/api/custom-areas/${userId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};

// Analytics Logging
export const logAnalytics = async (event) => {
  try {
    const response = await api.post('/api/analytics', { event });
    return { success: true, data: response.data };
  } catch (error) {
    return handleApiError(error);
  }
};