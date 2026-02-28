import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings:
    """
    Application settings loaded from environment variables with validation.
    """
    
    def __init__(self):
        # Earth Engine settings
        self.ee_project_id = self._get_env("EE_PROJECT_ID")
        if not self.ee_project_id:
            logger.critical("CRITICAL: EE_PROJECT_ID environment variable is not set!")
            logger.critical("Earth Engine functionality will be unavailable.")
        
        # Security settings
        self.secret_key = self._get_env("SECRET_KEY", "a-very-secret-key-for-development-only")
        
        # GenAI settings
        self.gemini_api_key = self._get_env("GEMINI_API_KEY")
        self.gemini_model = self._get_env("GEMINI_MODEL", "gemma-3-4b-it")
        
        # Server settings
        self.host = self._get_env("HOST", "0.0.0.0")
        self.port = int(self._get_env("PORT", "8000"))
        self.reload = self._get_env("RELOAD", "true").lower() == "true"
        
        # Firestore settings
        self.firebase_config = self._get_env("FIREBASE_CONFIG")
        self.google_application_credentials = self._get_env("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Rate limiting
        self.rate_limit_per_minute = int(self._get_env("RATE_LIMIT", "60"))
        
        # Concurrent operations 
        self.max_concurrent_ee_operations = int(self._get_env("MAX_CONCURRENT_EE_OPERATIONS", "5"))
        
        # Validate configuration
        self._validate_config()
    
    def _get_env(self, key: str, default: Optional[str] = None) -> str:
        """
        Get an environment variable or return a default value
        """
        value = os.environ.get(key, default)
        if value is None:
            logger.warning(f"Environment variable {key} not set")
        return value
    
    def _validate_config(self):
        """
        Validate configuration and log warnings for missing values
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set. GenAI functionality will be unavailable.")

    def __str__(self) -> str:
        """
        Return a string representation of the settings, masking sensitive values
        """
        return (
            f"Settings("
            f"ee_project_id={self.ee_project_id}, "
            f"secret_key={'*****' if self.secret_key else None}, "
            f"gemini_api_key={'*****' if self.gemini_api_key else None}, "
            f"gemini_model={self.gemini_model}, "
            f"host={self.host}, "
            f"port={self.port}, "
            f"reload={self.reload}, "
            f"firebase_config={'*****' if self.firebase_config else None}, "
            f"google_application_credentials={self.google_application_credentials}, "
            f"rate_limit_per_minute={self.rate_limit_per_minute}, "
            f"max_concurrent_ee_operations={self.max_concurrent_ee_operations}"
            f")"
        ) 