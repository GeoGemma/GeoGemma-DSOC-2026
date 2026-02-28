<img src="GeoGemma banner.png" alt="GeoGemma Banner" width="100%"/>

# GeoGemma: Earth Observation with Google Earth Engine & Gemma

**GeoGemma** is an innovative Earth observation application that combines Google Earth Engine's powerful imagery analysis with Gemma. It enables users to explore satellite imagery, analyze geospatial data, and extract insights through natural language prompts. This Solution is built to validate a Google Funded Research on GeoAI by the students of GDG on Campus Institute of Space Technology, Islamabad, Pakistan. 

## 📍 Features
GeoGemma supports the analysis of planetary-level geospatial data for the whole globe based on natural language prompts, with its custom-designed modules which include Normalized Difference Vegetation Index (NDVI), historical and latest satellite image view, Land Use/Land Cover Classification (LULC), surface water analysis, land surface temperature, GHGs mapping, open buildings display, flood mapping, forest cover and loss monitoring, and active fire monitoring both historically and in near real-time. These modules can be extended up to 100+ or more, based on industry usage, making GeoGemma scalable and extendable for applications across a wide range of sectors such as agriculture, hydrology, disaster monitoring, air quality monitoring, mining, and climate monitoring—making this product one of its kind.

**Example queries** to test out:
- Give me the latest satellite image of Manila from Sentinel-2 or Landsat 8.
- Show me ndvi in Amazon rainforest for year 2023.
- Display the thermal variations in dubai desert for year 2001.
- Visualize the flood water of Daharki, Sindh for August 2024.

These are not the only supported queries—GeoGemma allows a wide range of features through a modern UI that provides an interactive experience for users.

**Frontend tools for interaction:**
- Measurement and Drawing Tools: Calculate distances on the map, create points, lines, and polygons
- Layer Management: Zoom to layer, stack layers, control opacity and visibility
- Inspect: Get the value of variables at a particular point
- Detailed Metadata: Visualize map legends, value guides, and metadata including requested date, acquisition date, updated date, cloud cover, spatial resolution, bands, etc., along with detailed statistics like minimum, mean, maximum, and standard deviation

**Assistance tools:**

**AI Assistant Chat**: Chat with GeoGemma, which helps in analysis interpretation and guidance for the next prompt; discuss Earth science topics with the embedded GeoGemma chat feature.

**Earth Agent:** Try out one of the first geospatial MCP AI agents connected to multiple EO APIs like NASA, USGS, and Copernicus, powered by Gemini, to stay informed about updated climatic events in a selected area.

**Dataset Explorer**: The Dataset Explorer showcases all 900+ datasets from the GEE catalog for instant visualization. It is developed using a RAG (Retrieval-Augmented Generation) architecture, leveraging semantic search capabilities based on keywords. The results are categorized into themes such as DEM, climate, atmosphere, imagery, and more by clicking on it provides instant visualziation of all bands within defined time range with additional resources for the datasets.

**Comparison Analysis:** Compare imagery between different dates to detect changes for informed decision-making.

## 🚀 Getting Started

### Prerequisites

- Node.js (v18 or later)
- Python 3.8+
- Google Earth Engine account with access to the Earth Engine API
- Google Gemma/Gemini API key

### Environment Setup

1. Clone the repository:
   ```bash
   https://github.com/GeoGemma/GeoGemma-APAC-2025.git
   cd geogemma
   ```

2. Create and configure environment files:

   #### Backend (.env)
   ```
   EE_PROJECT_ID="your-ee-project-id"
   SECRET_KEY="your-secret-key"
   OLLAMA_BASE_URL="http://localhost:11434"  # If using Ollama
   OLLAMA_MODEL="gemma2:2b"  # If using Ollama
   ```

   #### Frontend (.env)
   ```
   VITE_API_URL=http://localhost:8000
   VITE_BACKEND_URL=http://localhost:8000
   VITE_GEMINI_API_KEY=your-gemini-api-key
   ```

3. Install dependencies:

   #### Backend
   ```bash
   pip install -r requirements.txt
   ```

   #### Frontend
   ```bash
   npm install
   ```

4. Authenticate with Earth Engine:
   ```bash
   earthengine authenticate
   ```

### Running the Application

1. Start the backend server:
   ```bash
   python app.py
   ```

2. Start the frontend development server:
   ```bash
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173`

The frontend would look something like this, with the sample prompt applied: **"Display the thermal variations in Dubai desert for the year 2001."**

<img src="GeoGemma frontend.png" alt="GeoGemma frontend" width="100%"/>

By clicking the Dataset Explorer button, a new window will open, providing an interactive experience with the GEE Data Catalog. Users can explore datasets by selecting specific bands or time ranges. Try searching for keywords like 'DEM', 'climate', or 'Landsat 8 imagery' to begin interacting with the data.

<img src="GEE Dataset explorer.png" alt="GEE dataset explorer" width="100%"/>


## 🏗️ Project Architecture

### Frontend (React + Vite)

- **Context API**: MapContext for global state management
- **Components**:
  - Map visualization using MapLibre GL JS
  - Chat interface with Gemma/Gemini (Earth Agent) integration
  - Layer management sidebar
  - Analysis tools for time series and comparisons
  - Responsive UI design with Google styling

### Backend (FastAPI)

- **Earth Engine Integration**: Processes and serves Earth Engine imagery
- **API Endpoints**:
  - `/api/analyze`: Natural language prompt analysis
  - `/api/metadata`: MetaData extraction
  - `/api/geometry`: Admin boundary extraction at different levels for the location.
  - `/api/layers`: Layer management
- **Prompt Analysis**: The Gemma model is configured with prompt engineering instructions to steer its behavior in extracting the analysis type, location, and date range from the user's prompt. These variables are then passed in JSON format to Earth Engine (EE) modules, where the desired function is executed by Google Earth Engine (GEE), and the resulting tile URL is generated and rendered on the frontend.The sample architecture chart visualizes the workflow.

<img src="architecture diagram.png" alt="architecture diagram" width="100%"/>

## 📁 Project Structure

```
geogemma/
├── app.py                  # FastAPI backend entry point
├── authenticate_ee.py      # Earth Engine authentication
├── ee_metadata.py          # Metadata extraction utilities
├── ee_modules/             # Earth Engine processing modules
│   ├── rgb.py              # RGB imagery processing
│   ├── ndvi.py             # NDVI processing
│   ├── water.py            # Surface water processing
│   ├── lulc.py             # Land use/cover processing
│   ├── lst.py              # Land surface temperature
│   └── openbuildings.py    # Building height analysis
├── ee_utils.py             # Earth Engine utility functions
├── src/                    # Frontend React application
│   ├── components/         # UI components
│   ├── contexts/           # React contexts
│   ├── services/           # API services
│   ├── styles/             # CSS styles
│   ├── utils/              # Utility functions
│   ├── App.jsx             # Main React component
│   └── main.jsx            # Frontend entry point
├── public/                 # Static assets
├── index.html              # HTML template
├── package.json            # NPM configuration
├── vite.config.js          # Vite configuration
└── README.md               # Project documentation
```


## 🛠️ Key Technologies

### Frontend
- **React**: UI library
- **MapLibre GL JS**: Interactive opensource mapping Library
- **Google Generative AI SDK**: Gemma/Gemini integration
- **TailwindCSS**: Styling
- **Vite**: Build tool and development server

### Backend
- **FastAPI**: API framework
- **Earth Engine Python API**: Satellite imagery processing
- **LangChain + Ollama**: Local LLM integration (optional)
- **Pydantic**: Data validation
- **Geopy**: Geocoding

## 🌐 Earth Engine Data Sources

- **Sentinel-2**: 10m resolution optical imagery (since 2015)
- **Landsat**: 30m resolution imagery (historical data since 1982)
- **JRC Global Surface Water**: Water presence and seasonality
- **ESA WorldCover**: Land cover classification
- **LST datasets**: Land surface temperature from Landsat thermal bands
- **Google Open Buildings**: Building footprints and heights

## 🔒 Authentication

The application requires authentication with Google Earth Engine:

1. Ensure you have an active Google Cloud account with Earth Engine API enabled
2. Create a service account with Earth Engine access
3. Set the `EE_PROJECT_ID` environment variable
4. Use `earthengine authenticate` or provide service account credentials


## Backend Architecture

The backend is built with FastAPI and follows a modular, service-oriented architecture:

```
backend/
  ├── src/
  │   ├── api/             # API routes
  │   │   └── routers/     # API route modules
  │   ├── config/          # Configuration
  │   ├── middleware/      # Middleware components
  │   ├── models/          # Data models
  │   ├── services/        # Service layer
  │   └── utils/           # Utility functions
  ├── ee_modules/          # Earth Engine modules
  ├── ee_config/           # Earth Engine configuration
  ├── app.py               # Application entry point
  ├── requirements.txt     # Python dependencies
  └── Dockerfile           # Docker configuration
```

### Key Components

- **API Layer**: Routes and endpoint handlers
- **Service Layer**: Business logic and external services
- **Models**: Data validation and schemas using Pydantic
- **Configuration**: Environment-based configuration
- **Middleware**: Cross-cutting concerns like rate limiting

## Environment Setup

Create a `.env` file in the project root with the following variables:

```
EE_PROJECT_ID=your-gcp-project-id
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemma-3-4b-it
SECRET_KEY=your-secret-key
```

## Running the Application

### Local Development

1. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

2. Run the application:

```bash
cd backend
python app.py
```

### Docker

```bash
cd backend
docker-compose up
```

## API Documentation

API documentation is available at `/api/docs` when the application is running.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Google Research & Google DeepMind under the Gemma Academic Program. 
- Google Earth Engine for satellite imagery and analysis capabilities.
- Google Gemma/Gemini for the conversational AI components and GeoAI Image retrival.
- MapLibre GL JS for the mapping visualization.
- The open-source community for various libraries and tools used in this project.
