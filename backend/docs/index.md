# GeoGemma Backend Documentation

Welcome to the GeoGemma backend documentation. This documentation covers the architecture, API, and development guide for the GeoGemma backend.

## Overview

GeoGemma is a web application for visualizing and analyzing Earth Engine data. It provides an easy-to-use interface for analyzing satellite imagery and geospatial data.

The backend is built with FastAPI and follows a modular, service-oriented architecture.

## Architecture

The backend is structured as follows:

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

## Setup and Installation

### Prerequisites

- Python 3.10+
- Google Cloud SDK
- Earth Engine Python API credentials

### Local Development

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r backend/requirements.txt`
5. Set up environment variables in a `.env` file
6. Run the application: `python app.py`

### Docker

1. Build the Docker image: `docker build -t geogemma-backend .`
2. Run the container: `docker run -p 8000:8000 geogemma-backend`

## API Documentation

API documentation is available at `/api/docs` when the application is running.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request 