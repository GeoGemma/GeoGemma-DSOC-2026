# GIS AI Agent

A powerful GIS (Geographic Information System) AI Agent built to analyze geographical and environmental data, provide insights, and support sustainability planning using modern AI technologies.

## Features

- Advanced geospatial analysis using Earth Engine and other GIS tools
- Climate analysis and environmental impact assessment
- Sustainability and resilience planning tools
- Data visualization and mapping
- Natural language processing for geospatial queries
- Real-time monitoring and alerting

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn/Gunicorn
- **AI/ML**: Google Gemini AI
- **Geospatial**: Earth Engine API, GeoPandas, Shapely, Rasterio, GDAL
- **Visualization**: Folium, Matplotlib, Plotly
- **Deployment**: Docker, Nginx
- **Caching & Performance**: Redis
- **Security**: JWT, SSL/TLS, Content Security Policy

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for containerized deployment)
- Google Cloud account with Earth Engine access
- Google Gemini API access
- (Optional) Firebase account for enhanced features

## Quick Start

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gis-ai-agent.git
   cd gis-ai-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up configuration:
   ```bash
   cp config/api_keys.yaml.example config/api_keys.yaml
   cp config/server_config.yaml.example config/server_config.yaml
   ```
   Edit these files to add your API keys and configure the server.

5. Run the application:
   ```bash
   python -m src.main --debug
   ```

### Production Deployment with Docker

1. Configure environment:
   ```bash
   cp .env.template .env
   ```
   Edit `.env` file with your production settings.

2. Build and start Docker containers:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. SSL Setup for HTTPS:
   - Place your SSL certificates in `nginx/ssl/` directory:
     - `fullchain.pem`: Full certificate chain
     - `privkey.pem`: Private key
   - Update domain name in `nginx/conf.d/gis-agent.conf`

4. Access the application:
   - API: `https://your-domain.com/api/`
   - Health check: `https://your-domain.com/health`

## Security Configuration

### API Keys and Credentials

- Never commit API keys or credentials to version control
- Use environment variables or configuration files outside of version control
- Rotate keys regularly and use minimal permissions

### Rate Limiting

Rate limiting is configured in both the application layer and Nginx:

- Configure application-level limits in `server_config.yaml`
- Adjust Nginx rate limits in `nginx/conf.d/gis-agent.conf`

### Authentication

JWT-based authentication is enabled by default for all API endpoints:

1. Configure in `server_config.yaml`:
   ```yaml
   security:
     enable_authentication: true
     jwt_secret: "your_secure_random_string"
     token_expiration_seconds: 86400
   ```

2. Request flow:
   - Get token: `POST /api/auth/token`
   - Use token: Include in `Authorization: Bearer <token>` header

## Monitoring and Maintenance

### Health Checks

- Basic health: `GET /health`
- Kubernetes liveness probe: `GET /health/live`
- Kubernetes readiness probe: `GET /health/ready`
- Detailed diagnostics (non-production only): `GET /diagnostics`

### Logs

- Application logs are stored in `logs/gis_agent.log` with rotation enabled
- Docker logs can be viewed with:
  ```bash
  docker-compose logs -f gis-agent
  ```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, feature requests, or questions, please open an issue on the GitHub repository. 