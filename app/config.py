"""
Configuration module for Load Logic
Loads environment variables from .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

# Default settings
DEFAULT_DEPARTURE_TIME = os.getenv("DEFAULT_DEPARTURE_TIME", "07:00").strip()
DEFAULT_SERVICE_MINUTES = int(os.getenv("DEFAULT_SERVICE_MINUTES", "20"))

# Logging
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
