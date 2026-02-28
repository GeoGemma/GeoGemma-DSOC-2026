"""
Configuration settings for GEE Dataset Explorer
"""
import os

class Config:
    """Application configuration settings"""
    # Keep only the dataset path
    DATASETS_PATH = os.environ.get(
        'DATASETS_PATH', 
        r"E:\A4 WEB DESIGN\Dataset-Explorer\enhanced_gee_catalog_20250425.pkl"
    )
    
    # Enhanced search configuration
    SEARCH_MODEL_SIZE = os.environ.get('SEARCH_MODEL_SIZE', 'small')  # small, medium, large
    SEARCH_CACHE_DIR = os.environ.get('SEARCH_CACHE_DIR', 'saved_indexes')
    
    # Field weights for search
    SEARCH_WEIGHTS = {
        'title': float(os.environ.get('WEIGHT_TITLE', '0.35')),
        'id': float(os.environ.get('WEIGHT_ID', '0.15')),
        'description': float(os.environ.get('WEIGHT_DESCRIPTION', '0.30')),
        'keywords': float(os.environ.get('WEIGHT_KEYWORDS', '0.20'))
    }
    
    # Other configuration settings
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    FEATURE_LIMIT = int(os.environ.get('FEATURE_LIMIT', '10000'))  # Default limit for feature collections
    
    # App specific settings
    APP_NAME = "GEE Dataset Explorer"
    APP_VERSION = "1.1.0"

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    # Use smaller models in development
    SEARCH_MODEL_SIZE = 'small'

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    # In production, you might want to use medium-sized models
    SEARCH_MODEL_SIZE = os.environ.get('SEARCH_MODEL_SIZE', 'small')