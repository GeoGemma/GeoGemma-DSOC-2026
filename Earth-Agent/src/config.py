"""
Configuration module for the GIS AI Agent.

This module handles loading and managing configuration from YAML files,
environment variables, and other sources.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the GIS AI Agent."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Path to the configuration directory. If not provided,
                        defaults to the 'config' directory in the project root.
        """
        if config_dir is None:
            # Use the default config directory relative to the project root
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        # Load configurations
        self.api_keys = self._load_config("api_keys.yaml")
        self.server_config = self._load_config("server_config.yaml")
        
        # Apply environment variable overrides
        self._apply_env_overrides()

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            filename: Name of the configuration file to load.

        Returns:
            Dictionary containing the configuration from the file.
        """
        config_path = self.config_dir / filename
        
        # If the file doesn't exist, try the example file
        if not config_path.exists() and not filename.endswith(".example"):
            example_path = self.config_dir / f"{filename}.example"
            if example_path.exists():
                logger.warning(f"Using example configuration from {example_path}")
                config_path = example_path
        
        # If the file still doesn't exist, return an empty dictionary
        if not config_path.exists():
            logger.warning(f"Configuration file {filename} not found in {self.config_dir}")
            return {}
        
        try:
            with open(config_path, "r") as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            return {}

    def _apply_env_overrides(self) -> None:
        """Apply overrides from environment variables to the configuration."""
        # Handle API keys from environment variables
        # For example, GEMINI_API_KEY environment variable would override gemini.api_key in the config
        if "GEMINI_API_KEY" in os.environ:
            if "gemini" not in self.api_keys:
                self.api_keys["gemini"] = {}
            self.api_keys["gemini"]["api_key"] = os.environ["GEMINI_API_KEY"]
        
        # Handle server configuration from environment variables
        if "SERVER_HOST" in os.environ:
            if "server" not in self.server_config:
                self.server_config["server"] = {}
            self.server_config["server"]["host"] = os.environ["SERVER_HOST"]
        
        # PORT environment variable takes priority (for Cloud Run)
        if "PORT" in os.environ:
            if "server" not in self.server_config:
                self.server_config["server"] = {}
            try:
                self.server_config["server"]["port"] = int(os.environ["PORT"])
                logger.info(f"Using PORT from environment: {os.environ['PORT']}")
            except ValueError:
                logger.warning(f"Invalid PORT in environment variable: {os.environ['PORT']}")
        # Fallback to SERVER_PORT if PORT is not set
        elif "SERVER_PORT" in os.environ:
            if "server" not in self.server_config:
                self.server_config["server"] = {}
            try:
                self.server_config["server"]["port"] = int(os.environ["SERVER_PORT"])
            except ValueError:
                logger.warning(f"Invalid server port in environment variable: {os.environ['SERVER_PORT']}")
        
        # Handle Firebase configuration
        firebase_config = self.api_keys.get("firebase", {})
        
        # Set Firebase environment variables from config if they don't exist
        if firebase_config:
            # Database URL
            if firebase_config.get("database_url"):
                os.environ["FIREBASE_DB_URL"] = firebase_config["database_url"]
                logger.info(f"Set FIREBASE_DB_URL from config: {firebase_config['database_url']}")
            else:
                logger.warning("Firebase database URL not found in configuration")
                
            # API Key
            if firebase_config.get("api_key"):
                os.environ["FIREBASE_API_KEY"] = firebase_config["api_key"]
                logger.info(f"Set FIREBASE_API_KEY from config")
            else:
                logger.warning("Firebase API key not found in configuration")
                
            # Encryption Key
            if firebase_config.get("encryption_key"):
                os.environ["FIREBASE_ENCRYPTION_KEY"] = firebase_config["encryption_key"]
                logger.info(f"Set FIREBASE_ENCRYPTION_KEY from config")
            else:
                logger.warning("Firebase encryption key not found in configuration")
        else:
            logger.warning("Firebase configuration not found in api_keys.yaml")

    def get_api_keys(self) -> Dict[str, Any]:
        """
        Get API keys configuration.

        Returns:
            Dictionary containing API keys configuration.
        """
        return self.api_keys

    def get_server_config(self) -> Dict[str, Any]:
        """
        Get server configuration.

        Returns:
            Dictionary containing server configuration.
        """
        return self.server_config

    def get_model_config(self) -> Dict[str, Any]:
        """
        Get model configuration.

        Returns:
            Dictionary containing model configuration.
        """
        return self.server_config.get("model", {})
    
    def get_tool_config(self) -> Dict[str, Any]:
        """
        Get tool configuration.

        Returns:
            Dictionary containing tool configuration.
        """
        return self.server_config.get("tools", {})


# Singleton instance
_config_manager = None


def get_config(config_dir: Optional[str] = None) -> ConfigManager:
    """
    Get the configuration manager instance.

    Args:
        config_dir: Path to the configuration directory. If provided,
                   a new ConfigManager instance will be created with this directory.

    Returns:
        An initialized ConfigManager.
    """
    global _config_manager
    
    if _config_manager is None or config_dir is not None:
        _config_manager = ConfigManager(config_dir)
    
    return _config_manager 