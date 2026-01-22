import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of app directory)
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
DEFAULT_DEPARTURE_TIME = os.getenv("DEFAULT_DEPARTURE_TIME", "07:00").strip()
DEFAULT_SERVICE_MINUTES = int(os.getenv("DEFAULT_SERVICE_MINUTES", "20"))
