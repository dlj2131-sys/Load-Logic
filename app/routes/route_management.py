"""
Route Management API Endpoints
Handles creation, listing, updating, and deletion of routes
"""

from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.models import CreateRouteRequest, CreateRouteResponse, GetRouteResponse, ListRoutesResponse, Route
from app.db import drivers_repo, routes_repo
from app.services.sms import send_route_sms_to_drivers

router = APIRouter(prefix="/api", tags=["routes"])


@router.get("/drivers")
def get_drivers() -> Dict[str, Any]:
    """Get all available drivers"""
    drivers = drivers_repo.get_all_drivers()
    return {
        "drivers": [d.model_dump() for d in drivers],
        "total": len(drivers),
    }


@router.get("/driver/{driver_id}")
def get_driver(driver_id: str) -> Dict[str, Any]:
    """Get a specific driver"""
    driver = drivers_repo.get_driver(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"driver": driver.model_dump()}


@router.post("/routes/create")
async def create_routes(request: Request, payload: CreateRouteRequest) -> JSONResponse:
    """
    Create routes from clustering result and send to drivers via SMS

    Expects: {
        "depot": {lat, lon},
        "stops": [...],
        "max_drivers": 6,
        "max_stops_per_driver": 7
    }

    This endpoint:
    1. Uses existing clustering logic to group stops
    2. Assigns clusters to available drivers
    3. Creates Route records persisted to routes.json
    4. Sends SMS notifications to drivers
    """
    try:
        # Get all available drivers
        drivers = drivers_repo.get_all_drivers()
        if not drivers:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No drivers available"},
            )

        # Get the clustering logic from existing services
        from app.services.delivery_router import DeliveryRouter

        # Store original stop details (with delivery info)
        original_stops = {}

        # Prepare stops for clustering
        stops_for_clustering = []
        for i, stop in enumerate(payload.stops):
            stop_id = f"stop_{i}"
            stops_for_clustering.append({
                "id": stop_id,
                "lat": float(stop.get("lat", 0)),
                "lon": float(stop.get("lon", 0)),
                "address": stop.get("address", f"Stop {i}"),
            })

            # Store original stop details for later retrieval
            original_stops[stop_id] = {
                "id": stop_id,
                "address": stop.get("address", f"Stop {i}"),
                "lat": float(stop.get("lat", 0)),
                "lon": float(stop.get("lon", 0)),
                "service_minutes": stop.get("service_minutes", 20),
                "access_instructions": stop.get("access_instructions"),
                "gate_code": stop.get("gate_code"),
                "tank_location": stop.get("tank_location"),
                "customer_notes": stop.get("customer_notes"),
                "payment_required": stop.get("payment_required", False),
            }

        # Run clustering
        router = DeliveryRouter(
            depot_location=(payload.depot["lat"], payload.depot["lon"]),
            num_trucks=min(payload.max_drivers, len(drivers)),
            max_stops_per_truck=payload.max_stops_per_driver,
        )

        clusters = router.cluster_stops(stops_for_clustering)

        # Assign clusters to drivers and create routes
        created_routes = []
        sms_info = []
        driver_list = drivers[:len(clusters)]  # Only use as many drivers as clusters

        for i, (cluster_id, cluster_stops) in enumerate(clusters.items()):
            if i >= len(driver_list):
                break

            driver = driver_list[i]

            # Optimize route order for this cluster
            ordered_stops = router.optimize_route(cluster_stops, use_google_maps=True)

            # Get ordered delivery IDs
            ordered_delivery_ids = [s["id"] for s in ordered_stops]

            # Generate Google Maps link
            from app.services.links import multi_stop_link
            addresses = [s["address"] for s in ordered_stops]
            google_maps_link = multi_stop_link(
                depot=f"{payload.depot['lat']},{payload.depot['lon']}",
                ordered_stops=addresses,
            )

            # Enrich cluster stops with original delivery details
            enriched_stops = [original_stops[s["id"]] for s in ordered_stops if s["id"] in original_stops]

            # Create route record with enriched stop data
            route = routes_repo.create_route(
                driver_id=driver.id,
                depot=payload.depot,
                stops=enriched_stops,
                ordered_deliveries=ordered_delivery_ids,
                google_maps_link=google_maps_link,
                feasible=True,
            )

            created_routes.append({
                "route_id": route.id,
                "driver_id": route.driver_id,
                "driver_name": driver.name,
                "ordered_deliveries": route.ordered_deliveries,
                "google_maps_link": route.google_maps_link,
                "num_stops": len(ordered_delivery_ids),
            })

            # Prepare SMS info
            sms_info.append({
                "driver": driver,
                "route_id": route.id,
            })

        # Send SMS notifications
        base_url = str(request.base_url).rstrip("/")
        sms_results = send_route_sms_to_drivers(sms_info, base_url=base_url)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "routes": created_routes,
                "sms_sent": sms_results,
                "error": None,
            },
        )

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "routes": [],
                "sms_sent": [],
            },
        )


@router.get("/routes")
def list_routes(status: str = None) -> ListRoutesResponse:
    """List all routes, optionally filtered by status"""
    routes = routes_repo.list_routes(status=status)
    active_count = len([r for r in routes if r.status == "active"])
    return ListRoutesResponse(
        routes=routes,
        total=len(routes),
        active_count=active_count,
    )


@router.get("/routes/{route_id}")
def get_route(route_id: str) -> GetRouteResponse:
    """Get a specific route"""
    route = routes_repo.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return GetRouteResponse(route=route)


@router.put("/routes/{route_id}")
def update_route(route_id: str, updates: Dict[str, Any]) -> GetRouteResponse:
    """Update a route (owner only)"""
    route = routes_repo.update_route(route_id, updates)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return GetRouteResponse(route=route)


@router.delete("/routes/{route_id}")
def cancel_route(route_id: str) -> Dict[str, Any]:
    """Cancel a route"""
    route = routes_repo.cancel_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"success": True, "route_id": route_id, "status": "cancelled"}


@router.get("/driver-route/{route_id}")
def get_driver_route(route_id: str) -> GetRouteResponse:
    """
    Get route for driver portal (public, no auth required)
    Returns route details for display on driver mobile interface
    """
    route = routes_repo.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Enrich with driver info
    driver = drivers_repo.get_driver(route.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    return GetRouteResponse(route=route)
