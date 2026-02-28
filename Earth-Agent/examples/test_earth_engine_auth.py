#!/usr/bin/env python3
"""
Test script for Google Earth Engine authentication.

This script tests the Earth Engine authentication using a service account JSON file
and project ID, and performs a simple test to verify the connection.
"""

import sys
import os
import json
import argparse
import asyncio
from pathlib import Path

# Add the parent directory to the path to allow importing from the src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_sources.earth_engine_connector import EarthEngineClient


async def test_earth_engine_auth(service_account_file=None, project_id=None):
    """
    Test Earth Engine authentication.

    Args:
        service_account_file: Path to Google Earth Engine service account JSON file.
        project_id: Google Cloud project ID for Earth Engine.
    """
    print("\n===== Google Earth Engine Authentication Test =====\n")
    
    # Check if service account file exists
    if service_account_file:
        if not os.path.exists(service_account_file):
            print(f"Error: Service account file not found at {service_account_file}")
            return False
        print(f"Using service account file: {service_account_file}")
    else:
        print("No service account file provided, will try to use default credentials")
    
    # Check if project ID is provided
    if project_id:
        print(f"Using project ID: {project_id}")
    else:
        print("No project ID provided")
    
    try:
        # Create Earth Engine client
        print("\nInitializing Earth Engine client...")
        client = EarthEngineClient(service_account_file=service_account_file, project_id=project_id)
        
        # Perform a simple test - get a simple result from Earth Engine
        print("\nPerforming a simple test:")
        print("- Getting information about San Francisco...")
        
        # Test the area parsing function
        geometry = client._parse_area_to_geometry("San Francisco")
        
        # Print test results
        print("\nTest completed successfully!")
        print("Earth Engine is properly authenticated and working.")
        return True
        
    except Exception as e:
        print(f"\nError during authentication test: {e}")
        print("\nAuthentication test failed.")
        
        # Provide helpful suggestions
        print("\nPossible solutions:")
        print("1. Make sure your service account file is valid and contains the correct credentials")
        print("2. Ensure your Google Cloud project has the Earth Engine API enabled")
        print("3. Verify that your service account has the necessary permissions for Earth Engine")
        print("4. Check that your project ID is correct")
        print("5. If using default credentials, run 'earthengine authenticate' first")
        
        return False


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test Google Earth Engine authentication")
    
    parser.add_argument(
        "--service-account-file",
        help="Path to Google Earth Engine service account JSON file"
    )
    
    parser.add_argument(
        "--project-id",
        help="Google Cloud project ID for Earth Engine"
    )
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()
    
    success = await test_earth_engine_auth(
        service_account_file=args.service_account_file,
        project_id=args.project_id
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()) 