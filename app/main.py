from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import config first to ensure .env file is loaded
import app.config  # noqa: F401

from app.services.maps import (
    compute_matrix_seconds,
    geocode_address,
    geocode_addresses,
    has_google_key,
)
from app.services.multi_planner import plan_multi_routes
from app.services.delivery_router import DeliveryRouter
from app.services.links import multi_stop_link
# Temporarily commented out - requires app.db module
# from app.routes.route_management import router as routes_router
# from app.routes.request_management import router as requests_router

app = FastAPI()

# Default depot for cluster-based routing (NYC)
_DEFAULT_DEPOT = (40.7589, -73.9851)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Temporarily commented out - requires app.db module
# app.include_router(routes_router)
# app.include_router(requests_router)


@app.get("/api/health")
def api_health() -> Dict[str, Any]:
    return {"ok": True, "api_key_configured": has_google_key()}


def _depot_from_payload(payload: Dict[str, Any]) -> tuple[float, float]:
    d = payload.get("depot")
    if isinstance(d, dict) and "lat" in d and "lon" in d:
        try:
            return (float(d["lat"]), float(d["lon"]))
        except (TypeError, ValueError):
            pass
    return _DEFAULT_DEPOT


def _stops_from_cluster_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = payload.get("stops", [])
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(raw):
        if not isinstance(s, dict):
            continue
        try:
            lat, lon = float(s["lat"]), float(s["lon"])
        except (TypeError, ValueError, KeyError):
            continue
        out.append({
            "id": s.get("id", i + 1),
            "lat": lat,
            "lon": lon,
            "address": (s.get("address") or "").strip() or f"Stop {i + 1}",
        })
    return out


def _split_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in (text or "").splitlines()]
    cleaned: List[str] = []
    for ln in lines:
        if not ln:
            continue
        ln2 = ln
        if len(ln2) > 3:
            while len(ln2) and ln2[0].isdigit():
                ln2 = ln2[1:]
            ln2 = ln2.lstrip().lstrip(".").lstrip(")").lstrip().lstrip()
        if ln2:
            cleaned.append(ln2)
    return cleaned


def _normalize_date(date_str: str) -> str:
    s = (date_str or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise ValueError(f"Invalid date format: {date_str!r}. Use YYYY-MM-DD or MM/DD/YYYY")


def _normalize_time(time_str: str) -> str:
    s = (time_str or "").strip().upper()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M")
        except ValueError:
            pass
    raise ValueError(f"Invalid time format: {time_str!r}. Use HH:MM or h:mm AM/PM")


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    """Serve customer booking landing page"""
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
        },
    )


@app.get("/owner/dashboard", response_class=HTMLResponse)
def owner_dashboard(request: Request):
    """Serve owner dashboard for managing requests and routes"""
    import app.config as _cfg
    return templates.TemplateResponse(
        "owner_dashboard.html",
        {
            "request": request,
            "has_google_key": has_google_key(),
            "default_departure": getattr(_cfg, "DEFAULT_DEPARTURE_TIME", "07:00") or "07:00",
            "default_service": getattr(_cfg, "DEFAULT_SERVICE_MINUTES", 20),
        },
    )


@app.get("/admin/route-planner", response_class=HTMLResponse)
def route_planner(request: Request):
    """Serve route planner (original index.html for admin use)"""
    import app.config as _cfg
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "has_google_key": has_google_key(),
            "default_departure": getattr(_cfg, "DEFAULT_DEPARTURE_TIME", "07:00") or "07:00",
            "default_service": getattr(_cfg, "DEFAULT_SERVICE_MINUTES", 20),
        },
    )


@app.get("/customer/track/{request_id}", response_class=HTMLResponse)
def customer_tracking(request: Request, request_id: str):
    """Serve customer tracking page"""
    return templates.TemplateResponse(
        "customer_tracking.html",
        {
            "request": request,
            "request_id": request_id,
        },
    )


@app.get("/driver/route/{route_id}", response_class=HTMLResponse)
def driver_route(request: Request, route_id: str):
    """Serve driver route page"""
    return templates.TemplateResponse(
        "driver_route.html",
        {
            "request": request,
            "route_id": route_id,
        },
    )


@app.post("/api/cluster")
def api_cluster(payload: Dict[str, Any]) -> JSONResponse:
    """Cluster stops into truck groups. Body: { depot?: {lat,lon}, stops: [...], num_trucks?: int, max_stops_per_truck?: int }."""
    stops = _stops_from_cluster_payload(payload)
    if not stops:
        return JSONResponse(status_code=400, content={"error": "No stops provided"})
    if len(stops) > 50:
        return JSONResponse(status_code=400, content={"error": "Maximum 50 stops allowed"})
    depot = _depot_from_payload(payload)
    num_trucks = int(payload.get("num_trucks", 6))
    max_stops = int(payload.get("max_stops_per_truck", 7))
    router = DeliveryRouter(depot, num_trucks=num_trucks, max_stops_per_truck=max_stops)
    clusters = router.cluster_stops(stops)
    result: Dict[str, Any] = {"success": True, "clusters": {}, "num_trucks": len(clusters)}
    for tid, truck_stops in clusters.items():
        result["clusters"][f"truck_{tid + 1}"] = {"stops": truck_stops, "count": len(truck_stops)}
    return JSONResponse(content=result)


@app.post("/api/optimize-route")
def api_optimize_route(payload: Dict[str, Any]) -> JSONResponse:
    """Optimize route for a single truck. Body: { depot?: {lat,lon}, stops: [...], use_google_maps?: bool }."""
    stops = _stops_from_cluster_payload(payload)
    if not stops:
        return JSONResponse(status_code=400, content={"error": "No stops provided"})
    depot = _depot_from_payload(payload)
    use_google = bool(payload.get("use_google_maps", True))
    router = DeliveryRouter(depot)
    route = router.optimize_route(stops, use_google_maps=use_google)
    metrics = router.get_route_metrics(route)
    return JSONResponse(content={"success": True, "route": route, "metrics": metrics})


@app.post("/api/full-routing-plan")
def api_full_routing_plan(payload: Dict[str, Any]) -> JSONResponse:
    """Full routing plan for all trucks. Body: { depot?: {lat,lon}, stops: [...], use_google_optimization?: bool, num_trucks?: int, max_stops_per_truck?: int }."""
    stops = _stops_from_cluster_payload(payload)
    if not stops:
        return JSONResponse(status_code=400, content={"error": "No stops provided"})
    if len(stops) > 50:
        return JSONResponse(status_code=400, content={"error": "Maximum 50 stops allowed"})
    depot = _depot_from_payload(payload)
    use_google = bool(payload.get("use_google_optimization", True))
    num_trucks = int(payload.get("num_trucks", 6))
    max_stops = int(payload.get("max_stops_per_truck", 7))
    router = DeliveryRouter(depot, num_trucks=num_trucks, max_stops_per_truck=max_stops)
    plan = router.create_full_routing_plan(stops, use_google_optimization=use_google)
    return JSONResponse(content={"success": True, "routing_plan": plan})


def _depot_str(depot: Dict[str, Any]) -> str:
    """Return depot as 'lat,lon' or 'address' for Google Maps URL."""
    if isinstance(depot, dict) and (depot.get("address") or "").strip():
        return (depot.get("address") or "").strip()
    if isinstance(depot, dict) and "lat" in depot and "lon" in depot:
        try:
            return f"{float(depot['lat'])},{float(depot['lon'])}"
        except (TypeError, ValueError):
            pass
    return f"{_DEFAULT_DEPOT[0]},{_DEFAULT_DEPOT[1]}"


def _ordered_addresses(stops: List[Dict[str, Any]]) -> List[str]:
    """Ordered list of address strings for waypoints (address or 'lat,lon')."""
    out: List[str] = []
    for i, s in enumerate(stops):
        if not isinstance(s, dict):
            continue
        addr = (s.get("address") or "").strip()
        if addr:
            out.append(addr)
        elif "lat" in s and "lon" in s:
            try:
                out.append(f"{float(s['lat'])},{float(s['lon'])}")
            except (TypeError, ValueError):
                pass
    return out


@app.post("/api/full-routing-plan-from-addresses")
async def api_full_routing_plan_from_addresses(payload: Dict[str, Any]) -> JSONResponse:
    """
    Geocode depot + stops (addresses), run cluster optimizer, return drivers with Google Maps links.
    Body: { depot_address, stops: [{address}] | stops_text }, use_google_optimization?, max_drivers?, max_stops_per_driver? }.
    Uses same inputs as plan_multi. Requires GOOGLE_MAPS_API_KEY (for geocoding).
    """
    if not has_google_key():
        return JSONResponse(
            status_code=400,
            content={
                "feasible": False,
                "error": "Cluster-from-addresses requires GOOGLE_MAPS_API_KEY (geocoding). Set it in .env.",
            },
        )
    depot_address = (payload.get("depot_address") or "").strip()
    if not depot_address:
        return JSONResponse(status_code=400, content={"feasible": False, "error": "Missing depot_address"})

    stops_text: List[str] = []
    if isinstance(payload.get("stops"), list):
        for s in payload["stops"]:
            addr = (s or {}).get("address", "")
            if addr and addr.strip():
                stops_text.append(addr.strip())
    else:
        stops_text = _split_lines(payload.get("stops_text", ""))
    if not stops_text:
        return JSONResponse(status_code=400, content={"feasible": False, "error": "No stops provided"})
    if len(stops_text) > 50:
        return JSONResponse(status_code=400, content={"feasible": False, "error": "Maximum 50 stops allowed"})

    depot_ll = await geocode_address(depot_address)
    if depot_ll is None:
        return JSONResponse(
            status_code=400,
            content={"feasible": False, "error": f"Could not geocode depot: {depot_address!r}"},
        )
    stop_geos = await geocode_addresses(stops_text)
    if len(stop_geos) != len(stops_text):
        failed = [a for a in stops_text if not any(s["address"] == a for s in stop_geos)]
        return JSONResponse(
            status_code=400,
            content={
                "feasible": False,
                "error": f"Could not geocode {len(failed)} stop(s).",
                "failed_addresses": failed[:10],
            },
        )

    use_google = bool(payload.get("use_google_optimization", True))
    num_trucks = int(payload.get("max_drivers", payload.get("num_trucks", 6)))
    max_stops = int(payload.get("max_stops_per_driver", payload.get("max_stops_per_truck", 7)))
    router = DeliveryRouter(depot_ll, num_trucks=num_trucks, max_stops_per_truck=max_stops)
    plan = router.create_full_routing_plan(
        stop_geos,
        use_google_optimization=use_google,
    )

    drivers: List[Dict[str, Any]] = []
    for key in sorted(plan.keys()):
        if key == "summary":
            continue
        truck = plan.get(key)
        if not isinstance(truck, dict):
            continue
        stops = truck.get("stops") or []
        addrs = _ordered_addresses(stops)
        if not addrs:
            continue
        link = multi_stop_link(depot_address, addrs)
        drivers.append({
            "driver": key.replace("_", " "),
            "google_maps_link": link,
            "ordered_deliveries": addrs,
            "feasible": True,
            "schedule": [],
            "lunch": "—",
        })

    return JSONResponse(content={
        "feasible": True,
        "drivers": drivers,
        "routes": drivers,
        "from_cluster": True,
    })


@app.post("/api/cluster-to-maps-routes")
def api_cluster_to_maps_routes(payload: Dict[str, Any]) -> JSONResponse:
    """
    Convert cluster result to driver routes with Google Maps links.
    Body: { depot: { lat, lon } | { address }, routing_plan: { Truck_1: { stops }, ... } }.
    Returns drivers in route-planner shape: driver, google_maps_link, ordered_deliveries, feasible, schedule, lunch.
    """
    depot = payload.get("depot")
    if not isinstance(depot, dict):
        depot = {}
    plan = payload.get("routing_plan") or {}
    depot_str = _depot_str(depot)

    drivers: List[Dict[str, Any]] = []
    for key in sorted(plan.keys()):
        if key == "summary":
            continue
        truck = plan.get(key)
        if not isinstance(truck, dict):
            continue
        stops = truck.get("stops") or []
        addrs = _ordered_addresses(stops)
        if not addrs:
            continue
        link = multi_stop_link(depot_str, addrs)
        drivers.append({
            "driver": key.replace("_", " "),
            "google_maps_link": link,
            "ordered_deliveries": addrs,
            "feasible": True,
            "schedule": [],
            "lunch": "—",
        })

    return JSONResponse(content={
        "feasible": True,
        "drivers": drivers,
        "routes": drivers,
        "from_cluster": True,
    })


@app.post("/api/route-metrics")
def api_route_metrics(payload: Dict[str, Any]) -> JSONResponse:
    """Metrics for a route. Body: { depot?: {lat,lon}, route: [{lat,lon,...}, ...] }."""
    route = payload.get("route", [])
    if not isinstance(route, list):
        return JSONResponse(status_code=400, content={"error": "No route provided"})
    clean: List[Dict[str, Any]] = []
    for i, s in enumerate(route):
        if not isinstance(s, dict):
            continue
        try:
            lat, lon = float(s["lat"]), float(s["lon"])
        except (TypeError, ValueError, KeyError):
            continue
        clean.append({"id": s.get("id", i + 1), "lat": lat, "lon": lon, "address": s.get("address", "")})
    if not clean:
        return JSONResponse(status_code=400, content={"error": "No valid route points"})
    depot = _depot_from_payload(payload)
    router = DeliveryRouter(depot)
    metrics = router.get_route_metrics(clean)
    return JSONResponse(content={"success": True, "metrics": metrics})


@app.post("/api/plan-and-cluster")
async def api_plan_and_cluster(payload: Dict[str, Any]) -> JSONResponse:
    """
    Unified route planning endpoint that handles mixed address/coordinate inputs.
    Geocodes addresses (if Google API available), clusters stops, optimizes routes.
    
    Body: {
      depot: { type: 'address' | 'coords', value: string | {lat, lon} },
      stops: [{ type: 'address' | 'coords', value: ... }, ...],
      max_drivers?: int,
      max_stops_per_driver?: int
    }
    """
    depot_input = payload.get("depot")
    stops_input = payload.get("stops", [])

    if not isinstance(depot_input, dict) or not depot_input.get("type"):
        return JSONResponse(status_code=400, content={"feasible": False, "error": "Invalid depot format"})
    
    if not isinstance(stops_input, list) or len(stops_input) == 0:
        return JSONResponse(status_code=400, content={"feasible": False, "error": "No stops provided"})

    if len(stops_input) > 50:
        return JSONResponse(status_code=400, content={"feasible": False, "error": "Maximum 50 stops allowed"})

    max_drivers = int(payload.get("max_drivers", 6))
    max_stops_per_driver = int(payload.get("max_stops_per_driver", 7))
    truck_capacity = float(payload.get("truck_capacity", 2000))

    # Parse depot
    try:
        if depot_input["type"] == "coords":
            depot_coords = depot_input.get("value")
            if not isinstance(depot_coords, dict) or "lat" not in depot_coords or "lon" not in depot_coords:
                return JSONResponse(status_code=400, content={"feasible": False, "error": "Invalid depot coordinates"})
            depot_ll = (float(depot_coords["lat"]), float(depot_coords["lon"]))
            depot_display = f"{depot_ll[0]},{depot_ll[1]}"
        else:  # address
            depot_address = (depot_input.get("value") or "").strip()
            if not depot_address:
                return JSONResponse(status_code=400, content={"feasible": False, "error": "Empty depot address"})
            
            if has_google_key():
                depot_ll = await geocode_address(depot_address)
                if depot_ll is None:
                    return JSONResponse(
                        status_code=400,
                        content={"feasible": False, "error": f"Could not geocode depot: {depot_address!r}"}
                    )
                depot_display = depot_address
            else:
                return JSONResponse(
                    status_code=400,
                    content={"feasible": False, "error": "Geocoding requires Google Maps API key. Use coordinates (lat,lon) instead."}
                )
    except (TypeError, ValueError) as e:
        return JSONResponse(status_code=400, content={"feasible": False, "error": f"Invalid depot: {str(e)}"})

    # Parse and geocode stops
    processed_stops: List[Dict[str, Any]] = []
    for i, stop_input in enumerate(stops_input):
        if not isinstance(stop_input, dict) or not stop_input.get("type"):
            return JSONResponse(status_code=400, content={"feasible": False, "error": f"Invalid stop format at index {i}"})
        
        try:
            # Extract gallons if provided
            gallons = stop_input.get("gallons")
            if gallons is not None:
                try:
                    gallons = float(gallons)
                    if gallons < 0:
                        gallons = 0
                except (TypeError, ValueError):
                    gallons = 0
            else:
                gallons = 0
            
            if stop_input["type"] == "coords":
                coords = stop_input.get("value")
                if not isinstance(coords, dict) or "lat" not in coords or "lon" not in coords:
                    return JSONResponse(status_code=400, content={"feasible": False, "error": f"Invalid coordinates at stop {i}"})
                processed_stops.append({
                    "id": i + 1,
                    "address": f"{float(coords['lat'])},{float(coords['lon'])}",
                    "lat": float(coords["lat"]),
                    "lon": float(coords["lon"]),
                    "gallons": gallons
                })
            else:  # address
                addr = (stop_input.get("value") or "").strip()
                if not addr:
                    return JSONResponse(status_code=400, content={"feasible": False, "error": f"Empty address at stop {i}"})
                
                if has_google_key():
                    geo = await geocode_address(addr)
                    if geo is None:
                        return JSONResponse(
                            status_code=400,
                            content={"feasible": False, "error": f"Could not geocode stop {i}: {addr!r}"}
                        )
                    processed_stops.append({
                        "id": i + 1,
                        "address": addr,
                        "lat": geo[0],
                        "lon": geo[1],
                        "gallons": gallons
                    })
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"feasible": False, "error": "Geocoding requires Google Maps API key. Use coordinates (lat,lon) instead."}
                    )
        except (TypeError, ValueError) as e:
            return JSONResponse(status_code=400, content={"feasible": False, "error": f"Invalid stop {i}: {str(e)}"})

    # Cluster and optimize
    try:
        print(f"DEBUG: Creating router with depot={depot_ll}, stops={len(processed_stops)}")
        router = DeliveryRouter(depot_ll, num_trucks=max_drivers, max_stops_per_truck=max_stops_per_driver, truck_capacity=truck_capacity)
        print(f"DEBUG: Starting full routing plan...")
        plan = router.create_full_routing_plan(processed_stops, use_google_optimization=has_google_key())
        print(f"DEBUG: Clustering complete")

        # Convert to driver routes with Google Maps links
        drivers: List[Dict[str, Any]] = []
        for key in sorted(plan.keys()):
            if key == "summary":
                continue
            truck = plan.get(key)
            if not isinstance(truck, dict):
                continue
            stops = truck.get("stops") or []
            addrs = _ordered_addresses(stops)
            if not addrs:
                continue
            link = multi_stop_link(depot_display, addrs)
            
            # Calculate total gallons for this route
            total_gallons = sum(s.get("gallons", 0) for s in stops)
            
            # Create delivery list with gallons info
            deliveries_with_gallons = []
            for stop in stops:
                addr = stop.get("address", "")
                if not addr and "lat" in stop and "lon" in stop:
                    addr = f"{stop['lat']},{stop['lon']}"
                if addr:
                    delivery = {"address": addr}
                    if stop.get("gallons", 0) > 0:
                        delivery["gallons"] = stop["gallons"]
                    deliveries_with_gallons.append(delivery)
            
            drivers.append({
                "driver": key.replace("_", " "),
                "google_maps_link": link,
                "ordered_deliveries": deliveries_with_gallons if deliveries_with_gallons else addrs,
                "feasible": total_gallons <= truck_capacity,
                "total_gallons": total_gallons,
                "truck_capacity": truck_capacity,
            })

        print(f"DEBUG: Returning {len(drivers)} drivers")
        return JSONResponse(content={
            "feasible": True,
            "drivers": drivers,
            "routes": drivers,
        })
    except Exception as e:
        print(f"ERROR in clustering: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"feasible": False, "error": f"Clustering error: {str(e)}"})


@app.post("/api/plan_multi")
async def api_plan_multi(payload: Dict[str, Any]):
    """
    Accepts either:
      date: "YYYY-MM-DD" OR "MM/DD/YYYY"
      departure_time: "HH:MM" OR "h:mm AM/PM"
    """
    try:
        date = _normalize_date(payload.get("date"))
        departure_time = _normalize_time(payload.get("departure_time"))
    except Exception as e:
        return JSONResponse(status_code=400, content={"feasible": False, "error": str(e)})

    depot_address = (payload.get("depot_address") or "").strip()
    default_service_minutes = int(payload.get("default_service_minutes", 20))
    max_drivers = int(payload.get("max_drivers", 5))
    max_stops_per_driver = int(payload.get("max_stops_per_driver", 8))
    print(f"api_plan_multi: Received parameters - max_drivers={max_drivers}, max_stops_per_driver={max_stops_per_driver}")
    work_window_start = payload.get("work_window_start", "08:00")
    work_window_end = payload.get("work_window_end", "18:00")
    lunch_window_start = payload.get("lunch_window_start", "11:30")
    lunch_window_end = payload.get("lunch_window_end", "13:00")
    lunch_minutes = int(payload.get("lunch_minutes", 30))
    lunch_skippable = bool(payload.get("lunch_skippable", True))

    if not depot_address:
        return JSONResponse(
            status_code=400,
            content={"feasible": False, "error": "Missing required field: depot_address"},
        )

    stops_text: List[str] = []
    if isinstance(payload.get("stops"), list):
        for s in payload["stops"]:
            addr = (s or {}).get("address", "")
            if addr and addr.strip():
                stops_text.append(addr.strip())
    else:
        stops_text_input = payload.get("stops_text", "")
        stops_text = _split_lines(stops_text_input)

    if not stops_text:
        return JSONResponse(status_code=400, content={"feasible": False, "error": "No stops provided"})

    # Convert stops from list of strings to list of dicts (as expected by plan_multi_routes)
    stops: List[Dict[str, Any]] = [{"address": addr} for addr in stops_text]

    # Build node list: depot + stops (function expects [depot] + stops, not [depot] + stops + [depot])
    # The function handles return to depot internally
    nodes = [depot_address] + stops_text
    
    print(f"api_plan_multi: {len(stops_text)} stops, {len(nodes)} nodes (1 depot + {len(stops_text)} stops)")

    try:
        print("api_plan_multi: computing matrix...")
        matrix_seconds, matrix_meta = await compute_matrix_seconds(nodes)
        print(f"api_plan_multi: matrix OK, size {len(matrix_seconds)}x{len(matrix_seconds[0]) if matrix_seconds else 0}")

        print("api_plan_multi: solving multi-route...")
        result = plan_multi_routes(
            depot_address=depot_address,
            stops=stops,
            durations_seconds=matrix_seconds,
            distances_meters=None,
            date_yyyy_mm_dd=date,
            departure_time=departure_time,
            work_window_start=work_window_start,
            work_window_end=work_window_end,
            lunch_window_start=lunch_window_start,
            lunch_window_end=lunch_window_end,
            lunch_minutes=lunch_minutes,
            lunch_skippable=lunch_skippable,
            default_service_minutes=default_service_minutes,
            max_drivers=max_drivers,
            max_stops_per_driver=max_stops_per_driver,
        )
        print(f"api_plan_multi: solve done. Result: feasible={result.get('feasible')}, drivers_used={result.get('drivers_used', 0)}, drivers_count={len(result.get('drivers', []))}")

        result["matrix"] = matrix_meta
        return JSONResponse(content=result)

    except Exception as e:
        # Always return JSON even on internal errors
        return JSONResponse(status_code=500, content={"feasible": False, "error": f"Internal error: {e}"})
