"""
Routes Repository
Manages route persistence to routes.json (mock database)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.models import Route


# Get the data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
ROUTES_FILE = DATA_DIR / "routes.json"


def _ensure_routes_file():
    """Ensure routes.json exists"""
    ROUTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ROUTES_FILE.exists():
        ROUTES_FILE.write_text("{}", encoding="utf-8")


def _load_routes_dict() -> Dict[str, Dict[str, Any]]:
    """Load routes dictionary from file"""
    _ensure_routes_file()
    try:
        with ROUTES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_routes_dict(routes: Dict[str, Dict[str, Any]]):
    """Save routes dictionary to file"""
    _ensure_routes_file()
    with ROUTES_FILE.open("w", encoding="utf-8") as f:
        json.dump(routes, f, indent=2, ensure_ascii=False)


def create_route(
    driver_id: str,
    depot: Dict[str, float],
    stops: List[Dict[str, Any]],
    ordered_deliveries: List[str],
    google_maps_link: Optional[str] = None,
    feasible: bool = True,
) -> Route:
    """Create a new route and save it"""
    route_id = str(uuid.uuid4())[:8]  # Short UUID for readability

    # Build stop objects with all delivery details
    route_stops = []
    for stop in stops:
        route_stops.append({
            "id": stop.get("id", f"stop_{uuid.uuid4().hex[:8]}"),
            "address": stop.get("address", ""),
            "lat": float(stop.get("lat", 0)),
            "lon": float(stop.get("lon", 0)),
            "service_minutes": int(stop.get("service_minutes", 20)),
            "access_instructions": stop.get("access_instructions"),
            "gate_code": stop.get("gate_code"),
            "tank_location": stop.get("tank_location"),
            "customer_notes": stop.get("customer_notes"),
            "payment_required": bool(stop.get("payment_required", False)),
        })

    route = Route(
        id=route_id,
        driver_id=driver_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        status="active",
        depot=depot,
        stops=route_stops,
        ordered_deliveries=ordered_deliveries,
        google_maps_link=google_maps_link,
        feasible=feasible,
        created_by_owner=True,
    )

    # Save to file
    routes = _load_routes_dict()
    routes[route_id] = route.model_dump()
    _save_routes_dict(routes)

    return route


def get_route(route_id: str) -> Optional[Route]:
    """Get a route by ID"""
    routes = _load_routes_dict()
    route_data = routes.get(route_id)
    if not route_data:
        return None

    try:
        return Route(**route_data)
    except Exception:
        return None


def list_routes(status: Optional[str] = None) -> List[Route]:
    """List all routes, optionally filtered by status"""
    routes = _load_routes_dict()
    result = []

    for route_data in routes.values():
        try:
            route = Route(**route_data)
            if status is None or route.status == status:
                result.append(route)
        except Exception:
            continue

    return sorted(result, key=lambda r: r.created_at, reverse=True)


def get_driver_route(driver_id: str) -> Optional[Route]:
    """Get the active route for a driver (one per driver)"""
    routes = list_routes(status="active")
    return next((r for r in routes if r.driver_id == driver_id), None)


def update_route(route_id: str, updates: Dict[str, Any]) -> Optional[Route]:
    """Update a route"""
    route = get_route(route_id)
    if not route:
        return None

    # Update allowed fields
    route_data = route.model_dump()
    allowed_updates = {
        "status": str,
        "ordered_deliveries": list,
        "stops": list,
    }

    for key, value in updates.items():
        if key in allowed_updates:
            route_data[key] = value

    # Save
    routes = _load_routes_dict()
    routes[route_id] = route_data
    _save_routes_dict(routes)

    try:
        return Route(**route_data)
    except Exception:
        return None


def cancel_route(route_id: str) -> Optional[Route]:
    """Cancel a route (mark as cancelled)"""
    return update_route(route_id, {"status": "cancelled"})


def complete_delivery(route_id: str, stop_id: str) -> Optional[Route]:
    """Mark a delivery stop as completed"""
    route = get_route(route_id)
    if not route:
        return None

    # Mark stop as completed (for future: add status field to RouteStop)
    # For now, just update the route
    route_data = route.model_dump()

    # TODO: Add delivery_status tracking per stop
    # routes[route_id]["deliveries"][stop_id]["status"] = "completed"

    routes = _load_routes_dict()
    routes[route_id] = route_data
    _save_routes_dict(routes)

    try:
        return Route(**route_data)
    except Exception:
        return None


def delete_route(route_id: str) -> bool:
    """Delete a route"""
    routes = _load_routes_dict()
    if route_id in routes:
        del routes[route_id]
        _save_routes_dict(routes)
        return True
    return False
