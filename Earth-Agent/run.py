#!/usr/bin/env python3
"""
Script to run the GIS AI Agent.

This is a simple wrapper script that imports and calls the main function
from the src.main module.
"""

import os
import sys
from pathlib import Path

# Disable Firebase
os.environ["DISABLE_FIREBASE"] = "true"
print("Firebase has been disabled for this run.")

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import the main function from src.main
from src.main import main

if __name__ == "__main__":
    # Call the main function
    main() 