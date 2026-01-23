from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================================
# Existing Models (Route Planning)
# ============================================================================

class StopRequest(BaseModel):
    address: str = Field(..., min_length=1)


class PlanRequest(BaseModel):
    date: str
    departure_time: Optional[str] = None
    depot_address: str
    stops: List[StopRequest]

    # Constraints
    work_window_start: str = "08:00"
    work_window_end: str = "18:00"
    lunch_window_start: str = "11:30"
    lunch_window_end: str = "13:00"
    lunch_minutes: int = 30
    lunch_skippable: bool = True

    default_service_minutes: int = 20


class PlanMultiRequest(PlanRequest):
    # Multi-driver controls
    max_drivers: int = 5
    max_stops_per_driver: int = 8


class PlanResponse(BaseModel):
    feasible: bool
    lunch: Optional[str] = ""
    schedule: List[Dict[str, Any]] = []
    google_maps_link: Optional[str] = None
    directions: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    matrix_bad_pairs: Optional[List[Dict[str, Any]]] = None


class DriverPlan(BaseModel):
    driver: str
    feasible: bool
    lunch: Optional[str] = ""
    schedule: List[Dict[str, Any]] = []
    ordered_deliveries: List[str] = []
    google_maps_link: Optional[str] = None
    error: Optional[str] = None


class PlanMultiResponse(BaseModel):
    feasible: bool
    drivers_used: int = 0
    drivers: List[DriverPlan] = []
    unassigned: List[str] = []
    error: Optional[str] = None
    matrix_bad_pairs: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# New Models (Driver Management & Route Persistence)
# ============================================================================

class Driver(BaseModel):
    id: str
    name: str
    phone: str
    vehicle: str
    capacity_gallons: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "driver_001",
                "name": "Driver 1",
                "phone": "+1-555-0101",
                "vehicle": "Truck A",
                "capacity_gallons": 10000
            }
        }


class RouteStop(BaseModel):
    id: str
    address: str
    lat: float
    lon: float
    service_minutes: int = 20
    access_instructions: Optional[str] = None
    gate_code: Optional[str] = None
    tank_location: Optional[str] = None
    customer_notes: Optional[str] = None
    payment_required: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "stop_001",
                "address": "123 Main St, City, ST",
                "lat": 40.7500,
                "lon": -73.9900,
                "service_minutes": 20,
                "access_instructions": "Gate code: 1234. Narrow driveway, go slow",
                "gate_code": "1234",
                "tank_location": "Left side of building, underground tank",
                "customer_notes": "Pets on premises - beware of dogs",
                "payment_required": False
            }
        }


class Route(BaseModel):
    id: str
    driver_id: str
    created_at: str  # ISO format datetime
    status: str = "active"  # active, completed, cancelled
    depot: Dict[str, float]  # {lat, lon}
    stops: List[RouteStop] = []
    ordered_deliveries: List[str] = []  # ordered stop IDs
    google_maps_link: Optional[str] = None
    feasible: bool = True
    created_by_owner: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "id": "route_001",
                "driver_id": "driver_001",
                "created_at": "2026-01-22T12:00:00Z",
                "status": "active",
                "depot": {"lat": 40.7589, "lon": -73.9851},
                "stops": [],
                "ordered_deliveries": ["stop_001", "stop_002"],
                "google_maps_link": "https://maps.google.com/...",
                "feasible": True,
                "created_by_owner": True
            }
        }


class CreateRouteRequest(BaseModel):
    depot: Dict[str, float]  # {lat, lon}
    stops: List[Dict[str, Any]]
    max_drivers: int = 6
    max_stops_per_driver: int = 7

    class Config:
        json_schema_extra = {
            "example": {
                "depot": {"lat": 40.7589, "lon": -73.9851},
                "stops": [
                    {"lat": 40.7500, "lon": -73.9900, "address": "123 Main St, City, ST"}
                ],
                "max_drivers": 6,
                "max_stops_per_driver": 7
            }
        }


class CreateRouteResponse(BaseModel):
    success: bool
    routes: List[Dict[str, Any]] = []
    sms_sent: List[Dict[str, str]] = []  # [{driver_id, phone, status}]
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "routes": [
                    {
                        "route_id": "route_001",
                        "driver_id": "driver_001",
                        "driver_name": "Driver 1",
                        "ordered_deliveries": ["stop_001", "stop_002"],
                        "google_maps_link": "https://maps.google.com/..."
                    }
                ],
                "sms_sent": [
                    {"driver_id": "driver_001", "phone": "+1-555-0101", "status": "sent"}
                ],
                "error": None
            }
        }


class GetRouteResponse(BaseModel):
    route: Optional[Route] = None
    error: Optional[str] = None


class ListRoutesResponse(BaseModel):
    routes: List[Route] = []
    total: int = 0
    active_count: int = 0


# ============================================================================
# Customer Delivery Request Models
# ============================================================================

class DeliveryRequest(BaseModel):
    id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    delivery_address: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    fuel_type: str
    heating_unit_type: str
    tank_location: str
    access_instructions: Optional[str] = None
    current_tank_level: str
    order_quantity_gallons: float
    tank_empty: bool
    requested_delivery_date: Optional[str] = None
    delivery_priority: str
    special_considerations: Optional[str] = None
    payment_method: str
    status: str = "pending"
    created_at: str
    assigned_route_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "req_abc123",
                "customer_name": "John Smith",
                "customer_email": "john@example.com",
                "customer_phone": "+1-555-0100",
                "delivery_address": "123 Main St, City, State",
                "lat": 40.7500,
                "lon": -73.9900,
                "fuel_type": "Heating Oil",
                "heating_unit_type": "Furnace",
                "tank_location": "Basement",
                "access_instructions": "Gate code 1234, beware of dogs",
                "current_tank_level": "25%",
                "order_quantity_gallons": 275,
                "tank_empty": False,
                "requested_delivery_date": "2026-01-25",
                "delivery_priority": "Standard",
                "special_considerations": "Call before arriving",
                "payment_method": "Credit Card",
                "status": "pending",
                "created_at": "2026-01-23T10:00:00Z",
                "assigned_route_id": None
            }
        }


class SubmitDeliveryRequestRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str
    delivery_address: str
    fuel_type: str
    heating_unit_type: str
    tank_location: str
    access_instructions: Optional[str] = None
    current_tank_level: str
    order_quantity_gallons: float
    tank_empty: bool
    requested_delivery_date: Optional[str] = None
    delivery_priority: str
    special_considerations: Optional[str] = None
    payment_method: str


class SubmitDeliveryRequestResponse(BaseModel):
    success: bool
    request_id: Optional[str] = None
    tracking_url: Optional[str] = None
    error: Optional[str] = None


class GetDeliveryRequestResponse(BaseModel):
    request: Optional[DeliveryRequest] = None
    error: Optional[str] = None


class ListDeliveryRequestsResponse(BaseModel):
    requests: List[DeliveryRequest] = []
    total: int = 0
    pending_count: int = 0


class DeliveryRequestStatusResponse(BaseModel):
    request: Optional[DeliveryRequest] = None
    assigned_route: Optional[Dict[str, Any]] = None
    driver: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BatchRequestsToRoutesRequest(BaseModel):
    request_ids: List[str]
    depot_address: str
    max_drivers: int = 6
    max_stops_per_driver: int = 7
    target_date: Optional[str] = None
