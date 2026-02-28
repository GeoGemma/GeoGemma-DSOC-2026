import os
import sys
import logging

# Get the absolute path to the directory containing this file
# This works even if __file__ is not defined
try:
    # When running as a script
    script_dir = os.path.abspath(os.path.dirname(__file__))
except NameError:
    # When running interactively
    script_dir = os.path.abspath(os.getcwd())

# Add the project root to Python path
sys.path.insert(0, script_dir)
sys.path.append("../..")
from flask import Flask
import ee
from utils.logging_config import setup_logging
from routes.main import register_main_routes
from routes.api import register_api_routes
from models.embedding_manager import DatasetEmbeddingManager
from config import Config

# Configure logging
logger = setup_logging()

def create_app(config_object=Config):
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Initialize Earth Engine with better error handling
    try:
        ee.Initialize(project='ee-gdgocist')
        logger.info("Earth Engine initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Earth Engine: {str(e)}")
        # Continue anyway, as we might be able to handle this later
    
    # Initialize the embedding manager
    logger.info(f"Initializing DatasetEmbeddingManager with model_size={config_object.SEARCH_MODEL_SIZE}")
    embedding_manager = DatasetEmbeddingManager(
        model_size=config_object.SEARCH_MODEL_SIZE
    )
    
    # Load datasets
    try:
        # Check if the datasets file exists
        if not os.path.exists(config_object.DATASETS_PATH):
            logger.error(f"Datasets file not found at path: {config_object.DATASETS_PATH}")
            raise FileNotFoundError(f"Datasets file not found: {config_object.DATASETS_PATH}")
            
        # Load the datasets
        embedding_manager.load_datasets(config_object.DATASETS_PATH)
        logger.info("Successfully loaded datasets and initialized search")
    except Exception as e:
        logger.error(f"Error loading datasets: {str(e)}")
        # This is critical, we may need to exit if this fails
        raise
    
    # Register routes
    register_main_routes(app)
    register_api_routes(app, embedding_manager)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)