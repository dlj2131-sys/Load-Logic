"""
Mock data store for driver mobile interface prototype.
In production, this would be replaced with database queries.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from copy import deepcopy

# ============================================================================
# MOCK DATA
# ============================================================================

_DRIVERS = [
    {
        "id": "driver-1",
        "name": "John Smith",
        "route_id": "route-2026-01-22-1",
    },
    {
        "id": "driver-2", 
        "name": "Maria Garcia",
        "route_id": "route-2026-01-22-2",
    },
    {
        "id": "driver-3",
        "name": "Mike Johnson",
        "route_id": None,  # No route assigned today
    },
]

_ROUTES = {
    "route-2026-01-22-1": {
        "id": "route-2026-01-22-1",
        "date": "2026-01-22",
        "driver_id": "driver-1",
        "depot": "1 Depot Rd, Newburgh, NY 12550",
        "status": "in_progress",
        "deliveries": [
            {
                "id": "del-101",
                "sequence": 1,
                "address": "67 Howell Rd, Campbell Hall, NY 10916",
                "customer_name": "Johnson Residence",
                "eta": "08:30",
                "status": "completed",
                "gate_code": None,
                "tank_location": "Left side of house, blue tank behind the fence",
                "access_notes": "Friendly dog in yard - will bark but harmless",
                "payment_required": False,
                "account_notes": "Long-time customer since 2015",
                "gallons_delivered": 150.5,
                "completion_notes": "Tank was nearly empty",
                "completed_at": "2026-01-22T08:45:00",
            },
            {
                "id": "del-102",
                "sequence": 2,
                "address": "135 S Plank Rd, Newburgh, NY 12550",
                "customer_name": "Newburgh Auto Shop",
                "eta": "09:15",
                "status": "in_progress",
                "gate_code": "4521",
                "tank_location": "Behind main building, 500 gallon tank on concrete pad",
                "access_notes": "Enter through back gate, not front entrance",
                "payment_required": True,
                "account_notes": "Commercial account - collect check on delivery",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
            {
                "id": "del-103",
                "sequence": 3,
                "address": "8 North St, Montgomery, NY 12549",
                "customer_name": "Williams Family",
                "eta": "10:00",
                "status": "pending",
                "gate_code": None,
                "tank_location": "Basement fill pipe on right side of house",
                "access_notes": "Narrow driveway - may need to back in",
                "payment_required": False,
                "account_notes": None,
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
            {
                "id": "del-104",
                "sequence": 4,
                "address": "45 Main St, Goshen, NY 10924",
                "customer_name": "Goshen Diner",
                "eta": "10:45",
                "status": "pending",
                "gate_code": "1234",
                "tank_location": "Underground tank, fill cap near dumpster area",
                "access_notes": "Delivery entrance on Oak Street side",
                "payment_required": True,
                "account_notes": "Manager Mike must sign receipt - call ahead if before 10am",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
            {
                "id": "del-105",
                "sequence": 5,
                "address": "100 Broadway, Newburgh, NY 12550",
                "customer_name": "Broadway Apartments",
                "eta": "11:30",
                "status": "pending",
                "gate_code": "9876",
                "tank_location": "Boiler room in basement - see super for access",
                "access_notes": "Park in loading zone, put hazards on. Ring super at unit 1A",
                "payment_required": False,
                "account_notes": "Building super: Carlos (555-0123)",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
        ],
    },
    "route-2026-01-22-2": {
        "id": "route-2026-01-22-2",
        "date": "2026-01-22",
        "driver_id": "driver-2",
        "depot": "1 Depot Rd, Newburgh, NY 12550",
        "status": "not_started",
        "deliveries": [
            {
                "id": "del-201",
                "sequence": 1,
                "address": "22 Lake Rd, Monroe, NY 10950",
                "customer_name": "Lake House B&B",
                "eta": "08:30",
                "status": "pending",
                "gate_code": None,
                "tank_location": "Two tanks behind garage - fill BOTH",
                "access_notes": "Long gravel driveway, watch for guests walking",
                "payment_required": True,
                "account_notes": "Seasonal business - verify they're open before delivery",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
            {
                "id": "del-202",
                "sequence": 2,
                "address": "55 Elm St, Bloomfield, NJ 07003",
                "customer_name": "Peterson Home",
                "eta": "09:30",
                "status": "pending",
                "gate_code": "5555",
                "tank_location": "Backyard, green tank next to shed",
                "access_notes": "Two large dogs - owner will secure them if called ahead",
                "payment_required": False,
                "account_notes": "Prefers morning deliveries",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
            {
                "id": "del-203",
                "sequence": 3,
                "address": "789 Valley Rd, Warwick, NY 10990",
                "customer_name": "Valley View Farm",
                "eta": "10:30",
                "status": "pending",
                "gate_code": None,
                "tank_location": "Large tank by barn, 1000 gallon capacity",
                "access_notes": "Farm equipment may be in driveway - honk and wait",
                "payment_required": False,
                "account_notes": "Farm account - billed monthly",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
            {
                "id": "del-204",
                "sequence": 4,
                "address": "12 Church St, Chester, NY 10918",
                "customer_name": "St. Mary's Church",
                "eta": "11:15",
                "status": "pending",
                "gate_code": None,
                "tank_location": "Rectory building behind church, tank on north side",
                "access_notes": "Do not block handicap parking spaces",
                "payment_required": False,
                "account_notes": "Non-profit account - tax exempt",
                "gallons_delivered": None,
                "completion_notes": None,
                "completed_at": None,
            },
        ],
    },
}

# Runtime state - stores modifications during session
_runtime_routes = None


def _get_routes() -> Dict[str, Any]:
    """Get routes dict, initializing runtime copy if needed."""
    global _runtime_routes
    if _runtime_routes is None:
        _runtime_routes = deepcopy(_ROUTES)
    return _runtime_routes


def reset_mock_data():
    """Reset all mock data to initial state. Useful for testing."""
    global _runtime_routes
    _runtime_routes = None


# ============================================================================
# PUBLIC API
# ============================================================================

def get_drivers() -> List[Dict[str, Any]]:
    """Get list of all drivers."""
    return deepcopy(_DRIVERS)


def get_driver(driver_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific driver by ID."""
    for driver in _DRIVERS:
        if driver["id"] == driver_id:
            return deepcopy(driver)
    return None


def get_route_for_driver(driver_id: str) -> Optional[Dict[str, Any]]:
    """Get the route assigned to a driver."""
    driver = get_driver(driver_id)
    if not driver or not driver.get("route_id"):
        return None
    
    routes = _get_routes()
    route = routes.get(driver["route_id"])
    return deepcopy(route) if route else None


def get_delivery(delivery_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific delivery by ID."""
    routes = _get_routes()
    for route in routes.values():
        for delivery in route["deliveries"]:
            if delivery["id"] == delivery_id:
                return deepcopy(delivery)
    return None


def get_delivery_with_route_info(delivery_id: str) -> Optional[Dict[str, Any]]:
    """Get delivery with additional route context."""
    routes = _get_routes()
    for route in routes.values():
        for i, delivery in enumerate(route["deliveries"]):
            if delivery["id"] == delivery_id:
                result = deepcopy(delivery)
                result["route_id"] = route["id"]
                result["depot"] = route["depot"]
                result["total_stops"] = len(route["deliveries"])
                # Find next delivery
                if i + 1 < len(route["deliveries"]):
                    result["next_delivery_id"] = route["deliveries"][i + 1]["id"]
                else:
                    result["next_delivery_id"] = None
                return result
    return None


def start_delivery(delivery_id: str) -> bool:
    """Mark a delivery as in_progress."""
    routes = _get_routes()
    for route in routes.values():
        for delivery in route["deliveries"]:
            if delivery["id"] == delivery_id:
                if delivery["status"] == "pending":
                    delivery["status"] = "in_progress"
                    return True
    return False


def complete_delivery(
    delivery_id: str,
    gallons_delivered: float,
    notes: Optional[str] = None
) -> bool:
    """Mark a delivery as complete and log the details."""
    routes = _get_routes()
    for route in routes.values():
        for delivery in route["deliveries"]:
            if delivery["id"] == delivery_id:
                delivery["status"] = "completed"
                delivery["gallons_delivered"] = gallons_delivered
                delivery["completion_notes"] = notes
                delivery["completed_at"] = datetime.now().isoformat()
                
                # Check if all deliveries are complete
                all_complete = all(d["status"] == "completed" for d in route["deliveries"])
                if all_complete:
                    route["status"] = "completed"
                elif route["status"] == "not_started":
                    route["status"] = "in_progress"
                
                return True
    return False


def get_route_progress(route_id: str) -> Dict[str, Any]:
    """Get completion stats for a route."""
    routes = _get_routes()
    route = routes.get(route_id)
    if not route:
        return {"total": 0, "completed": 0, "pending": 0, "in_progress": 0}
    
    deliveries = route["deliveries"]
    return {
        "total": len(deliveries),
        "completed": sum(1 for d in deliveries if d["status"] == "completed"),
        "pending": sum(1 for d in deliveries if d["status"] == "pending"),
        "in_progress": sum(1 for d in deliveries if d["status"] == "in_progress"),
    }
