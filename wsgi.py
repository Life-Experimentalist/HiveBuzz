"""
WSGI entry point for HiveBuzz application
For hosting on PythonAnywhere or similar services
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the application directory to the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Import the Flask app
from app import app as application

# Log startup information
logger.info(f"Starting HiveBuzz WSGI application from {app_dir}")

# For PythonAnywhere or any WSGI server
if __name__ == "__main__":
    application.run()
