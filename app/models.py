from __future__ import annotations

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


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
