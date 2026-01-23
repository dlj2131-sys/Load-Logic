"""
Delivery Request Repository
Handles persistence of customer delivery requests to JSON file
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models import DeliveryRequest


def _get_data_dir() -> Path:
    """Get the data directory path"""
    return Path(__file__).parent.parent.parent / "data"


def _get_requests_file() -> Path:
    """Get the requests.json file path"""
    return _get_data_dir() / "requests.json"


def _ensure_requests_file() -> None:
    """Ensure requests.json exists, create if not"""
    data_dir = _get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    requests_file = _get_requests_file()
    if not requests_file.exists():
        requests_file.write_text(json.dumps({}, indent=2))


def _load_requests_dict() -> Dict[str, Any]:
    """Load all requests from JSON file"""
    _ensure_requests_file()
    try:
        content = _get_requests_file().read_text()
        return json.loads(content) if content.strip() else {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_requests_dict(requests_dict: Dict[str, Any]) -> None:
    """Save requests dictionary to JSON file"""
    _ensure_requests_file()
    _get_requests_file().write_text(json.dumps(requests_dict, indent=2))


def create_request(
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    delivery_address: str,
    fuel_type: str,
    heating_unit_type: str,
    tank_location: str,
    current_tank_level: str,
    order_quantity_gallons: float,
    tank_empty: bool,
    delivery_priority: str,
    payment_method: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    access_instructions: Optional[str] = None,
    requested_delivery_date: Optional[str] = None,
    special_considerations: Optional[str] = None,
) -> DeliveryRequest:
    """Create a new delivery request"""
    request_id = str(uuid.uuid4())[:8]
    created_at = datetime.utcnow().isoformat() + "Z"

    request = DeliveryRequest(
        id=request_id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        lat=lat,
        lon=lon,
        fuel_type=fuel_type,
        heating_unit_type=heating_unit_type,
        tank_location=tank_location,
        access_instructions=access_instructions,
        current_tank_level=current_tank_level,
        order_quantity_gallons=order_quantity_gallons,
        tank_empty=tank_empty,
        requested_delivery_date=requested_delivery_date,
        delivery_priority=delivery_priority,
        special_considerations=special_considerations,
        payment_method=payment_method,
        status="pending",
        created_at=created_at,
        assigned_route_id=None,
    )

    # Save to file
    requests_dict = _load_requests_dict()
    requests_dict[request_id] = request.model_dump()
    _save_requests_dict(requests_dict)

    return request


def get_request(request_id: str) -> Optional[DeliveryRequest]:
    """Get a specific request by ID"""
    requests_dict = _load_requests_dict()
    request_data = requests_dict.get(request_id)

    if not request_data:
        return None

    return DeliveryRequest(**request_data)


def list_requests(status: Optional[str] = None) -> List[DeliveryRequest]:
    """List all requests, optionally filtered by status"""
    requests_dict = _load_requests_dict()
    requests = []

    for request_data in requests_dict.values():
        if status and request_data.get("status") != status:
            continue
        requests.append(DeliveryRequest(**request_data))

    # Sort by created_at descending (newest first)
    requests.sort(key=lambda r: r.created_at, reverse=True)
    return requests


def update_request(request_id: str, updates: Dict[str, Any]) -> Optional[DeliveryRequest]:
    """Update a request with new data"""
    requests_dict = _load_requests_dict()

    if request_id not in requests_dict:
        return None

    request_data = requests_dict[request_id]
    request_data.update(updates)

    _save_requests_dict(requests_dict)

    return DeliveryRequest(**request_data)


def assign_to_route(request_id: str, route_id: str) -> Optional[DeliveryRequest]:
    """Assign a request to a route and update status"""
    return update_request(
        request_id,
        {
            "status": "assigned",
            "assigned_route_id": route_id,
        }
    )


def complete_request(request_id: str) -> Optional[DeliveryRequest]:
    """Mark a request as completed"""
    return update_request(request_id, {"status": "completed"})


def cancel_request(request_id: str) -> Optional[DeliveryRequest]:
    """Cancel a request"""
    return update_request(request_id, {"status": "cancelled"})


def delete_request(request_id: str) -> bool:
    """Delete a request"""
    requests_dict = _load_requests_dict()

    if request_id not in requests_dict:
        return False

    del requests_dict[request_id]
    _save_requests_dict(requests_dict)
    return True
