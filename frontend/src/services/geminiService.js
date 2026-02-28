// src/services/geminiService.js
import { GoogleGenerativeAI } from "@google/generative-ai";

// Initialize the Gemini API with your API key
const API_KEY = import.meta.env.VITE_GEMINI_API_KEY;
const genAI = new GoogleGenerativeAI(API_KEY);

/**
 * Send a message to Gemini and get a response
 * @param {string} prompt - The user's message
 * @param {Array} history - Previous messages in the conversation
 * @returns {Promise<string>} - Gemini's response
 */
export async function chatWithGemini(prompt, history = []) {
  try {
    // For text-only input
    const model = genAI.getGenerativeModel({ model: "gemma-3-4b-it" });
    
    // Convert the history to the format expected by Gemini
    const formattedHistory = history.map(msg => ({
      role: msg.sender === 'user' ? 'user' : 'model',
      parts: [{ text: msg.text }]
    }));
    
    // Create the system instruction as a properly formatted message
    const systemInstruction = {
      role: "user",
      parts: [{
        text: "You are GeoGemma, an AI assistant specialized in Earth observation, satellite imagery, and geospatial analysis. Answer questions about satellite imaging, remote sensing, Earth science, and help interpret geospatial data. When users ask about analyzing specific locations, suggest they use the search bar with prompts like 'Show NDVI in [location]' or 'Surface water in [location]'. The application supports: RGB imagery, NDVI (vegetation index), Surface Water detection, Land Use/Land Cover (LULC), Land Surface Temperature (LST), and building height analysis. Keep your responses concise and focused on helping the user understand Earth observation concepts or guiding them to use the application effectively. For complex Earth science topics, provide clear, accessible explanations."
      }]
    };
    
    const systemResponse = {
      role: "model",
      parts: [{
        text: "I understand my role. I am GeoGemma, an AI assistant specialized in Earth observation, satellite imagery, and geospatial analysis. I'll provide concise and helpful information about satellite imaging, remote sensing, and Earth science. When users ask about specific locations, I'll suggest using the search bar with prompts like 'Show NDVI in [location]' or 'Surface water in [location]'. I'll keep my responses clear and accessible, especially for complex topics."
      }]
    };
    
    // Add system instruction and response to the beginning of the conversation
    const completeHistory = formattedHistory.length > 0 
      ? [systemInstruction, systemResponse, ...formattedHistory]
      : [systemInstruction, systemResponse];
    
    // Start a chat session
    const chat = model.startChat({
      history: completeHistory,
      generationConfig: {
        temperature: 0.7,
        topK: 40,
        topP: 0.95,
        maxOutputTokens: 1024,
      },
    });

    // Send the message and get a response
    const result = await chat.sendMessage(prompt);
    const response = result.response.text();
    
    return response;
  } catch (error) {
    console.error("Error communicating with Gemini:", error);
    throw error;
  }
}

/**
 * Process Earth observation prompts with Gemini to extract parameters
 * @param {string} prompt - The user's query about Earth observation
 * @returns {Promise<Object>} - Extracted parameters for visualization
 */
export async function analyzeEarthObservationPrompt(prompt) {
  try {
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-pro" });
    
    // Create messages including system instruction as user message
    const messages = [
      {
        role: "user",
        parts: [{
          text: "You are a geospatial analysis assistant. Your task is to analyze Earth observation prompts to extract structured parameters. Extract: location, processing type (RGB, NDVI, Surface Water, LULC, LST, or Building Heights), dates (if any), and other relevant parameters. Return a JSON object with the extracted information."
        }]
      },
      {
        role: "model",
        parts: [{
          text: "I understand. I'll analyze Earth observation prompts and extract structured parameters into JSON format."
        }]
      },
      {
        role: "user",
        parts: [{
          text: `Extract parameters from this Earth observation query: "${prompt}". Return ONLY a valid JSON object with keys: location, processing_type, start_date, end_date.`
        }]
      }
    ];
    
    // Start a chat session with messages
    const chat = model.startChat({
      history: messages.slice(0, 2),  // Start with system instruction and response
      generationConfig: {
        temperature: 0.2,
        topK: 1,
        topP: 0.95,
        maxOutputTokens: 1024,
      },
    });

    const result = await chat.sendMessage(messages[2].parts[0].text);
    const response = result.response.text();
    
    // Extract JSON from the response
    const jsonMatch = response.match(/```json\n([\s\S]*)\n```/) || 
                     response.match(/```\n([\s\S]*)\n```/) || 
                     response.match(/\{[\s\S]*\}/);
                     
    if (jsonMatch) {
      try {
        return JSON.parse(jsonMatch[1] || jsonMatch[0]);
      } catch (e) {
        console.error("Failed to parse JSON from Gemini response", e);
        throw new Error("Invalid response format");
      }
    } else {
      throw new Error("Could not extract parameters");
    }
  } catch (error) {
    console.error("Error analyzing prompt with Gemini:", error);
    throw error;
  }
}
