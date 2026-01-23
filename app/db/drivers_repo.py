"""
Driver Repository
Loads driver data from drivers.json (mock database)
"""

import json
from pathlib import Path
from typing import List, Optional

from app.models import Driver


# Get the data directory (parent of app -> Load-Logic -> data)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DRIVERS_FILE = DATA_DIR / "drivers.json"


def load_drivers() -> List[Driver]:
    """Load all drivers from drivers.json"""
    if not DRIVERS_FILE.exists():
        return []

    try:
        with DRIVERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        drivers = []
        for item in data:
            try:
                drivers.append(Driver(**item))
            except Exception:
                # Skip invalid driver records
                continue
        return drivers
    except Exception:
        return []


def get_all_drivers() -> List[Driver]:
    """Get all drivers"""
    return load_drivers()


def get_driver(driver_id: str) -> Optional[Driver]:
    """Get a specific driver by ID"""
    drivers = load_drivers()
    return next((d for d in drivers if d.id == driver_id), None)


def driver_exists(driver_id: str) -> bool:
    """Check if a driver exists"""
    return get_driver(driver_id) is not None
