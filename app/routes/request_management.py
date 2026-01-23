"""
Request Management API Endpoints
Handles customer delivery request submissions, listing, and batching to routes
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models import (
    DeliveryRequest,
    SubmitDeliveryRequestRequest,
    SubmitDeliveryRequestResponse,
    GetDeliveryRequestResponse,
    ListDeliveryRequestsResponse,
    DeliveryRequestStatusResponse,
    BatchRequestsToRoutesRequest,
)
from app.db import requests_repo
from app.db import drivers_repo, routes_repo
from app.services.maps import geocode_address, has_google_key
from app.services.delivery_router import DeliveryRouter
from app.services.links import multi_stop_link

router = APIRouter(prefix="/api", tags=["requests"])


@router.post("/booking")
async def submit_booking(payload: Dict[str, Any]) -> JSONResponse:
    """
    Submit a customer delivery request (from booking form)

    Expected fields from form:
    - customer_name, customer_email, customer_phone (mobile_number)
    - delivery_address
    - fuel_type, heating_unit_type, tank_location
    - access_instructions, current_tank_level, order_quantity_gallons
    - tank_empty, requested_delivery_date, delivery_priority
    - special_considerations, payment_method
    """
    try:
        # Map form field names (camelCase) to API field names (snake_case)
        customer_name = (payload.get("name") or payload.get("customer_name") or "").strip()
        customer_email = (payload.get("email") or payload.get("customer_email") or "").strip()
        customer_phone = (payload.get("phone") or payload.get("customer_phone") or payload.get("mobile_number") or "").strip()
        delivery_address = (payload.get("address") or payload.get("delivery_address") or "").strip()

        # Validate required fields
        if not all([customer_name, customer_email, customer_phone, delivery_address]):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Missing required fields"}
            )

        # Geocode address if Google Maps API available
        lat, lon = None, None
        if has_google_key():
            result = await geocode_address(delivery_address)
            if result:
                lat, lon = result
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": f"Could not geocode address: {delivery_address}"}
                )

        # Create delivery request
        request = requests_repo.create_request(
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            lat=lat,
            lon=lon,
            fuel_type=payload.get("fuelType") or payload.get("fuel_type") or "",
            heating_unit_type=payload.get("heatingUnit") or payload.get("heating_unit_type") or "",
            tank_location=payload.get("tankLocation") or payload.get("tank_location") or "",
            access_instructions=payload.get("accessInstructions") or payload.get("access_instructions"),
            current_tank_level=payload.get("tankLevel") or payload.get("current_tank_level") or "",
            order_quantity_gallons=float(payload.get("orderQuantity") or payload.get("order_quantity_gallons") or 0),
            tank_empty=payload.get("tankEmpty") == "on" or payload.get("tank_empty") == True,
            requested_delivery_date=payload.get("deliveryDate") or payload.get("requested_delivery_date"),
            delivery_priority=payload.get("deliveryPriority") or payload.get("delivery_priority") or "Standard",
            special_considerations=payload.get("specialConsiderations") or payload.get("special_considerations"),
            payment_method=payload.get("paymentMethod") or payload.get("payment_method") or "",
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "request_id": request.id,
                "tracking_url": f"/customer/track/{request.id}",
                "error": None
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@router.get("/requests")
def list_requests(status: str = None) -> ListDeliveryRequestsResponse:
    """List all delivery requests, optionally filtered by status"""
    requests_list = requests_repo.list_requests(status=status)
    pending_count = len([r for r in requests_list if r.status == "pending"])

    return ListDeliveryRequestsResponse(
        requests=requests_list,
        total=len(requests_list),
        pending_count=pending_count,
    )


@router.get("/requests/{request_id}")
def get_request(request_id: str) -> GetDeliveryRequestResponse:
    """Get a specific delivery request"""
    request = requests_repo.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return GetDeliveryRequestResponse(request=request)


@router.get("/requests/{request_id}/status")
def get_request_status(request_id: str) -> DeliveryRequestStatusResponse:
    """Get request status and assignment info (public endpoint for customers)"""
    request = requests_repo.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    assigned_route = None
    driver = None

    if request.assigned_route_id:
        route = routes_repo.get_route(request.assigned_route_id)
        if route:
            assigned_route = {
                "id": route.id,
                "status": route.status,
                "google_maps_link": route.google_maps_link,
                "ordered_deliveries": route.ordered_deliveries,
            }

            # Get driver info
            driver_obj = drivers_repo.get_driver(route.driver_id)
            if driver_obj:
                driver = {
                    "name": driver_obj.name,
                    "vehicle": driver_obj.vehicle,
                }

    return DeliveryRequestStatusResponse(
        request=request,
        assigned_route=assigned_route,
        driver=driver,
    )


@router.post("/requests/batch-to-routes")
async def batch_requests_to_routes(payload: BatchRequestsToRoutesRequest) -> JSONResponse:
    """
    Convert a batch of customer requests to driver routes

    Accepts list of request_ids and routing parameters.
    Converts requests to stops, clusters them, creates routes, and assigns to drivers.
    """
    try:
        # Get all available drivers
        drivers = drivers_repo.get_all_drivers()
        if not drivers:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No drivers available"}
            )

        # Load all requests and filter to requested IDs
        all_requests = {r.id: r for r in requests_repo.list_requests()}
        selected_requests = [all_requests[rid] for rid in payload.request_ids if rid in all_requests]

        if not selected_requests:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No valid requests selected"}
            )

        # Convert requests to stops format for clustering
        stops_for_clustering = []
        request_map = {}  # Map stop_id to request_id

        for req in selected_requests:
            if not req.lat or not req.lon:
                continue

            stop_id = f"stop_{req.id}"
            stops_for_clustering.append({
                "id": stop_id,
                "lat": req.lat,
                "lon": req.lon,
                "address": req.delivery_address,
            })
            request_map[stop_id] = req

        if not stops_for_clustering:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No requests with valid coordinates"}
            )

        # Parse depot address (use default NYC if not provided)
        depot_address = payload.depot_address.strip()
        if has_google_key():
            depot_coords = await geocode_address(depot_address)
            if not depot_coords:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": f"Could not geocode depot: {depot_address}"}
                )
            depot_location = depot_coords
        else:
            # Default to NYC
            depot_location = (40.7589, -73.9851)

        # Cluster stops
        router = DeliveryRouter(
            depot_location=depot_location,
            num_trucks=min(payload.max_drivers, len(drivers)),
            max_stops_per_truck=payload.max_stops_per_driver,
        )
        clusters = router.cluster_stops(stops_for_clustering)

        # Create routes from clusters
        created_routes = []
        driver_list = drivers[:len(clusters)]

        for i, (cluster_id, cluster_stops) in enumerate(clusters.items()):
            if i >= len(driver_list):
                break

            driver = driver_list[i]

            # Optimize route order
            ordered_stops = router.optimize_route(cluster_stops, use_google_maps=True)
            ordered_stop_ids = [s["id"] for s in ordered_stops]

            # Create stop data with original request details
            enriched_stops = []
            for stop in ordered_stops:
                request = request_map.get(stop["id"])
                if request:
                    enriched_stops.append({
                        "id": request.id,
                        "address": request.delivery_address,
                        "lat": request.lat,
                        "lon": request.lon,
                        "service_minutes": 20,
                        "access_instructions": request.access_instructions,
                        "gate_code": None,
                        "tank_location": request.tank_location,
                        "customer_notes": request.special_considerations,
                        "payment_required": False,
                    })

            # Generate Google Maps link
            addresses = [s["address"] for s in enriched_stops]
            google_maps_link = multi_stop_link(
                depot=depot_address if has_google_key() else f"{depot_location[0]},{depot_location[1]}",
                ordered_stops=addresses,
            )

            # Create route
            route = routes_repo.create_route(
                driver_id=driver.id,
                depot={"lat": depot_location[0], "lon": depot_location[1]},
                stops=enriched_stops,
                ordered_deliveries=[r.id for r in enriched_stops],
                google_maps_link=google_maps_link,
                feasible=True,
            )

            created_routes.append({
                "route_id": route.id,
                "driver_id": driver.id,
                "driver_name": driver.name,
                "num_stops": len(enriched_stops),
            })

            # Update request statuses
            for request in [r for r in enriched_stops]:
                requests_repo.assign_to_route(request["id"], route.id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "routes": created_routes,
                "error": None
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.put("/requests/{request_id}")
def update_request(request_id: str, updates: Dict[str, Any]) -> GetDeliveryRequestResponse:
    """Update a delivery request"""
    request = requests_repo.update_request(request_id, updates)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return GetDeliveryRequestResponse(request=request)


@router.delete("/requests/{request_id}")
def cancel_request(request_id: str) -> Dict[str, Any]:
    """Cancel a delivery request"""
    request = requests_repo.cancel_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"success": True, "request_id": request_id, "status": "cancelled"}
