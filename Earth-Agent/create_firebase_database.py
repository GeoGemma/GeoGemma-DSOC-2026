#!/usr/bin/env python
"""
Create Firebase Database Guide.

This script helps guide you through creating a Firebase Realtime Database
and configuring it for use with the GIS Agent.
"""

import logging
import sys
import os
import json
import subprocess
import requests
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("firebase_creator")

# Add the project root to Python path
sys.path.insert(0, '.')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create and configure Firebase database")
    parser.add_argument("--install", action="store_true", help="Install required packages")
    parser.add_argument("--disable", action="store_true", help="Disable Firebase and run the server")
    parser.add_argument("--check", action="store_true", help="Check if Firebase database exists")
    return parser.parse_args()

def install_packages():
    """Install required packages."""
    required_packages = ['firebase-admin', 'requests']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"Package {package} is already installed.")
        except ImportError:
            logger.info(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                logger.info(f"Successfully installed {package}.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install {package}: {e}")
                return False
    
    return True

def get_firebase_config():
    """Get Firebase configuration from environment or config file."""
    # Try to import config if available
    try:
        from src.config import get_config
        config = get_config()
        firebase_config = config.get_api_keys().get("firebase", {})
        
        # Set environment variables from config
        if firebase_config:
            if firebase_config.get("database_url"):
                os.environ["FIREBASE_DB_URL"] = firebase_config["database_url"]
                logger.info(f"Using database URL from config: {firebase_config['database_url']}")
            
            if firebase_config.get("api_key"):
                os.environ["FIREBASE_API_KEY"] = firebase_config["api_key"]
                logger.info("Using API key from config")
            
            if firebase_config.get("encryption_key"):
                os.environ["FIREBASE_ENCRYPTION_KEY"] = firebase_config["encryption_key"]
                logger.info("Using encryption key from config")
    except:
        logger.warning("Could not load config. Using environment variables only.")
    
    # Get configuration from environment variables
    db_url = os.environ.get("FIREBASE_DB_URL")
    api_key = os.environ.get("FIREBASE_API_KEY")
    
    # Format database URL
    if db_url:
        # Add 'https://' prefix if missing
        if not db_url.startswith("http"):
            db_url = f"https://{db_url}"
        
        # Add firebaseio.com suffix if missing
        if not "firebaseio.com" in db_url:
            if not db_url.endswith("."):
                db_url = f"{db_url}."
            db_url = f"{db_url}firebaseio.com"
        
        # Remove trailing slash
        if db_url.endswith('/'):
            db_url = db_url[:-1]
    
    # Try to extract project ID from database URL
    project_id = None
    if db_url and "-default-rtdb" in db_url:
        try:
            project_id = db_url.split("//")[1].split("-default-rtdb")[0]
        except:
            pass
    
    return {
        "database_url": db_url,
        "api_key": api_key,
        "project_id": project_id
    }

def check_database_exists(config):
    """Check if the Firebase database exists."""
    db_url = config.get("database_url")
    api_key = config.get("api_key")
    
    if not db_url:
        logger.error("No database URL configured")
        return False
    
    # Add .json suffix for REST API
    test_url = f"{db_url}/.json"
    if api_key:
        test_url += f"?auth={api_key}"
    
    try:
        response = requests.get(test_url)
        if response.status_code == 200:
            logger.info("✅ Database exists and is accessible")
            return True
        elif response.status_code in (401, 403):
            logger.info("✅ Database exists but requires authentication")
            return True
        elif response.status_code == 404:
            logger.error("❌ Database does not exist")
            return False
        else:
            logger.error(f"❌ Error checking database: {response.status_code}")
            logger.error(response.text)
            return False
    except Exception as e:
        logger.error(f"❌ Error connecting to database: {e}")
        return False

def show_manual_creation_steps(config):
    """Show steps for manually creating a Firebase database."""
    project_id = config.get("project_id")
    db_url = config.get("database_url")
    
    if not project_id and not db_url:
        logger.error("Cannot determine project ID or database URL. Please check your configuration.")
        return
    
    logger.info("\n===== FIREBASE DATABASE CREATION GUIDE =====")
    logger.info("Your Firebase database does not exist yet. Please follow these steps:")
    
    if project_id:
        logger.info(f"1. Go to https://console.firebase.google.com/project/{project_id}/database")
    else:
        logger.info("1. Go to https://console.firebase.google.com/ and select your project")
        logger.info("   Then navigate to 'Realtime Database' in the left sidebar")
    
    logger.info("2. Click 'Create Database'")
    logger.info("3. Choose your preferred location (usually the closest to your users)")
    logger.info("4. Start in 'Test mode' for easier setup")
    logger.info("5. Click 'Enable' to create the database")
    logger.info("6. Verify your database URL matches what's in your configuration")
    
    if db_url:
        logger.info(f"   Expected URL: {db_url}")
    
    logger.info("\nAfter creating the database, run this script with the --check flag to verify")
    logger.info("====================================\n")

def run_with_disabled_firebase():
    """Run the GIS Agent with Firebase disabled."""
    # Disable Firebase
    os.environ["DISABLE_FIREBASE"] = "true"
    
    # Try to run the server through the run helper
    run_script = Path("run_with_disabled_firebase.py")
    
    if not run_script.exists():
        logger.error("Could not find run_with_disabled_firebase.py")
        return False
    
    try:
        logger.info("Running GIS Agent with Firebase disabled")
        subprocess.call([sys.executable, str(run_script)])
        return True
    except Exception as e:
        logger.error(f"Error running server: {e}")
        return False

def main():
    """Main function."""
    args = parse_args()
    
    logger.info("Starting Firebase database creation")
    
    # Install required packages if requested
    if args.install:
        if not install_packages():
            logger.error("Failed to install required packages")
            return 1
    
    # Get Firebase configuration
    config = get_firebase_config()
    
    # If --disable flag is provided, run with Firebase disabled
    if args.disable:
        return 0 if run_with_disabled_firebase() else 1
    
    # Check if database exists if --check flag is provided
    if args.check:
        if check_database_exists(config):
            logger.info("✅ Firebase database setup complete!")
            return 0
        else:
            logger.error("❌ Firebase database setup failed")
            show_manual_creation_steps(config)
            return 1
    
    # By default, check if database exists and show steps if needed
    if check_database_exists(config):
        logger.info("✅ Firebase database is already set up!")
        return 0
    else:
        show_manual_creation_steps(config)
        
        # Ask if the user wants to run with Firebase disabled instead
        print("\nWould you like to run the GIS Agent with Firebase disabled? (y/n): ", end="")
        response = input().strip().lower()
        if response == 'y':
            return 0 if run_with_disabled_firebase() else 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 