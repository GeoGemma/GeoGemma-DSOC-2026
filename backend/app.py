# --- Entry point for the backend API ---
import os
import logging
from dotenv import load_dotenv

# Import FastAPI components
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Import configuration
from src.config.settings import Settings

# Import API routers
from src.api.routers import (
    analysis_router,
    layers_router,
    user_router,
    chat_router,
    custom_areas_router,
    health_router,
    pixel_value_router
)

# Import middleware
from src.middleware.rate_limit import RateLimitMiddleware

# Import static files handling
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app")

# Set specific logger levels
logging.getLogger("ee_utils").setLevel(logging.WARNING)
logging.getLogger("ee_metadata").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Create settings
settings = Settings()

# Initialize FastAPI app
app = FastAPI(
    title="Earth Engine Map App",
    description="A web app for visualizing Earth Engine data with Metadata",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=3600,
    same_site="lax"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(health_router, tags=["Health Check"])
app.include_router(analysis_router, prefix="/api", tags=["Analysis"])
app.include_router(layers_router, prefix="/api", tags=["Layers"])
app.include_router(user_router, prefix="/api", tags=["Users"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(custom_areas_router, prefix="/api", tags=["Custom Areas"])
app.include_router(pixel_value_router.router, prefix="/api", tags=["Pixel Values"])

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    from src.services.earth_engine_service import initialize_earth_engine
    from src.services.genai_service import initialize_genai
    
    # Initialize Earth Engine
    await initialize_earth_engine(settings.ee_project_id)
    
    # Initialize GenAI
    await initialize_genai()
    
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Application shutdown")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)