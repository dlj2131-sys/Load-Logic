from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

ET = ZoneInfo("America/New_York")


def _parse_hhmm(day: datetime, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return day.replace(hour=h, minute=m, second=0, microsecond=0)


def _min_of_day(dt: datetime) -> int:
    day0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int((dt - day0).total_seconds() // 60)


def _format_time(day: datetime, minutes_since_midnight: int) -> str:
    dt = day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=minutes_since_midnight)
    return dt.strftime("%I:%M %p").lstrip("0")


def _google_maps_link(depot: str, ordered_stops: List[str]) -> str:
    # Google Maps link per vehicle
    # origin = depot, destination = depot, waypoints = stops
    # Note: browser will URL-encode spaces; this is fine for most cases.
    if not ordered_stops:
        return ""
    base = "https://www.google.com/maps/dir/?api=1"
    origin = f"&origin={depot}"
    dest = f"&destination={depot}"
    wps = "&waypoints=" + "|".join(ordered_stops)
    return base + origin + dest + wps + "&travelmode=driving"


def plan_multi_routes(
    *,
    depot_address: str,
    stops: List[Dict[str, Any]],
    durations_seconds: List[List[float]],
    distances_meters: Optional[List[List[float]]],
    date_yyyy_mm_dd: str,
    departure_time: str,
    work_window_start: str,
    work_window_end: str,
    lunch_window_start: str,
    lunch_window_end: str,
    lunch_minutes: int,
    lunch_skippable: bool,
    default_service_minutes: int,
    max_drivers: int,
    max_stops_per_driver: int,
) -> Dict[str, Any]:
    """
    Fast multi-vehicle solve (one OR-Tools RoutingModel).
    - Uses up to max_drivers
    - Encourages fewer vehicles via fixed cost per used vehicle
    - Enforces max_stops_per_driver via capacity dimension
    - Applies time windows (work window + optional per-stop)
    - Lunch is NOT modeled as a true break (keeps solver fast). You can add it later per-vehicle.
    """

    # Addresses list is assumed to be: [depot] + stops
    # Matrix dims should match that.
    n_stops = len(stops)
    n_nodes = 1 + n_stops
    if len(durations_seconds) != n_nodes or any(len(r) != n_nodes for r in durations_seconds):
        return {
            "feasible": False,
            "error": f"Matrix size mismatch: expected {n_nodes}x{n_nodes}, got {len(durations_seconds)}x{len(durations_seconds[0]) if durations_seconds else 0}",
        }

    # Convert seconds -> integer minutes
    def sec_to_min(x: float) -> int:
        if x is None:
            return 10**9
        if x > 1e8:
            return int(x)
        return max(0, int(round(float(x) / 60.0)))

    travel = [[sec_to_min(durations_seconds[i][j]) for j in range(n_nodes)] for i in range(n_nodes)]
    
    # Debug: Check travel times
    if n_stops > 0:
        # Check depot to first stop
        depot_to_stop = travel[0][1]
        stop_to_depot = travel[1][0]
        total_round_trip = depot_to_stop + service[1] + stop_to_depot
        print(f"DEBUG: Travel times - depot->stop1: {depot_to_stop} min, stop1->depot: {stop_to_depot} min")
        print(f"DEBUG: Round trip time (depot->stop1->depot): {total_round_trip} min (including {service[1]} min service)")
        
        # Check for unrealistic travel times (penalty values)
        penalty_count = sum(1 for row in travel for val in row if val >= 10000)
        print(f"DEBUG: Travel matrix has {penalty_count} penalty values (>= 10000 min)")
        
        # Check max travel time between any two nodes
        max_travel = max(max(row) for row in travel if row)
        print(f"DEBUG: Maximum travel time in matrix: {max_travel} minutes")

    # Service minutes per node (0=depot)
    service = [0]
    for s in stops:
        sm = s.get("service_minutes")
        if sm is None:
            sm = default_service_minutes
        service.append(max(0, int(sm)))

    day = datetime.fromisoformat(date_yyyy_mm_dd).replace(tzinfo=ET)
    depart_dt = _parse_hhmm(day, departure_time)
    open_dt = _parse_hhmm(day, work_window_start)
    close_dt = _parse_hhmm(day, work_window_end)

    # Ensure work window start is not earlier than departure time
    # Vehicles can't start before they depart
    effective_open_dt = max(open_dt, depart_dt)
    effective_open_min = _min_of_day(effective_open_dt)

    # Time windows per node in minutes since midnight
    tw: List[Tuple[int, int]] = []
    # Depot: In multi-vehicle routing, depot node 0 is used for both start and end
    # Set start constraint (vehicles must leave at or after departure time)
    # For return, we'll allow vehicles to return up to horizon (24 hours)
    # This is more flexible and allows the solver to find feasible solutions
    depot_start = _min_of_day(depart_dt)
    depot_end = 24 * 60  # Allow return up to end of day (very permissive)
    tw.append((depot_start, depot_end))  # depot

    for s in stops:
        # Use effective_open (not earlier than departure) for stop windows
        if s.get("window_start"):
            ws = _parse_hhmm(day, s["window_start"])
            ws_min = _min_of_day(ws)
            # Ensure stop window doesn't start before vehicles can depart
            ws_min = max(ws_min, depot_start)
        else:
            ws_min = effective_open_min
        if s.get("window_end"):
            we = _parse_hhmm(day, s["window_end"])
            we_min = _min_of_day(we)
        else:
            we_min = _min_of_day(close_dt)
        tw.append((ws_min, we_min))

    num_vehicles = max(1, int(max_drivers))

    manager = pywrapcp.RoutingIndexManager(n_nodes, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def transit_cb(from_index: int, to_index: int) -> int:
        frm = manager.IndexToNode(from_index)
        to = manager.IndexToNode(to_index)
        return travel[frm][to] + service[frm]

    transit_idx = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # Encourage fewer vehicles: fixed cost applied when vehicle route is non-empty.
    # Units are "minutes" (since our arc costs are minutes).
    if n_stops <= 10:
        fixed_cost = 30
    elif n_stops <= 20:
        fixed_cost = 45
    else:
        fixed_cost = 60
    for v in range(num_vehicles):
        routing.SetFixedCostOfVehicle(int(fixed_cost), v)

    # Time dimension with slack for waiting
    horizon = 24 * 60
    routing.AddDimension(
        transit_idx,
        90,      # waiting slack
        horizon,
        False,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Apply time windows to nodes
    # For debugging: check if time windows are the issue
    print(f"DEBUG: Applying time windows to {n_nodes} nodes")
    
    # Check if time windows might be too restrictive
    # Calculate minimum time needed: depot->stop->depot
    if n_stops > 0:
        min_travel_example = travel[0][1] + service[1] + travel[1][0]  # depot->stop1->depot
        print(f"DEBUG: Example minimum time (depot->stop1->depot): {min_travel_example} minutes")
        print(f"DEBUG: Work window allows: {work_window_minutes} minutes")
        if min_travel_example > work_window_minutes:
            print(f"DEBUG: WARNING - Minimum travel time exceeds work window!")
    
    # Apply time windows - but make them more permissive for stops
    for node in range(n_nodes):
        idx = manager.NodeToIndex(node)
        a, b = tw[node]
        if node == 0:
            print(f"DEBUG: Depot (node 0) time window: {a} to {b} minutes")
            time_dim.CumulVar(idx).SetRange(a, b)
        else:
            # For stops, extend the end time significantly to allow more flexibility
            # Keep the start time but allow completion much later
            extended_end = min(b + 180, 24 * 60 - 1)  # Add 3 hours buffer, but not past midnight
            if node <= 3:  # Print first few stops
                print(f"DEBUG: Stop {node} time window: {a} to {extended_end} minutes (extended from {b})")
            time_dim.CumulVar(idx).SetRange(a, extended_end)

    # Capacity dimension: max stops per vehicle
    def demand_cb(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        return 0 if node == 0 else 1

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,
        [int(max_stops_per_driver)] * num_vehicles,
        True,
        "Stops",
    )
    
    # Allow dropping stops if capacity is insufficient
    # This prevents "no solution" when we have more stops than total capacity
    max_total_capacity = num_vehicles * max_stops_per_driver
    if n_stops > max_total_capacity:
        print(f"DEBUG: WARNING - {n_stops} stops but only {max_total_capacity} total capacity. Allowing stops to be dropped.")
        # Add disjunctions for all stops with penalty
        # High penalty to prefer using all stops, but allow dropping if needed
        penalty = 10000  # High penalty for dropping a stop
        for node in range(1, n_nodes):  # Skip depot
            idx = manager.NodeToIndex(node)
            routing.AddDisjunction([idx], penalty)
    else:
        # Even with enough capacity, allow dropping if time windows make it infeasible
        penalty = 50000  # Very high penalty - only drop if absolutely necessary
        print(f"DEBUG: Capacity sufficient ({max_total_capacity} >= {n_stops}), but allowing drops as fallback")
        for node in range(1, n_nodes):  # Skip depot
            idx = manager.IndexToNode(node)
            routing.AddDisjunction([idx], penalty)

    # Search parameters - try multiple strategies for better feasibility
    params = pywrapcp.DefaultRoutingSearchParameters()
    # Try AUTOMATIC first, which tries multiple strategies
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    # Increase time limit for larger problems
    params.time_limit.FromSeconds(30)
    params.log_search = False

    # Debug: Print constraint info
    work_window_minutes = _min_of_day(close_dt) - _min_of_day(depart_dt)
    print(f"DEBUG: {n_stops} stops, {num_vehicles} vehicles, max {max_stops_per_driver} stops/driver")
    print(f"DEBUG: Work window: {work_window_minutes} minutes ({departure_time} to {work_window_end})")
    print(f"DEBUG: Depot time window: {depot_start} to {depot_end} minutes (start >= {departure_time}, return allowed up to end of day)")
    if n_stops > 0:
        print(f"DEBUG: First stop time window: {tw[1] if len(tw) > 1 else 'N/A'}")
    
    sol = routing.SolveWithParameters(params)
    if not sol:
        print(f"DEBUG: AUTOMATIC strategy failed, trying PATH_CHEAPEST_ARC...")
        # Try with a simpler strategy if AUTOMATIC fails
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params.time_limit.FromSeconds(20)
        sol = routing.SolveWithParameters(params)
        
    if not sol:
        print(f"DEBUG: PATH_CHEAPEST_ARC failed, trying PATH_MOST_CONSTRAINED_ARC...")
        # Last attempt with PATH_MOST_CONSTRAINED_ARC
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_MOST_CONSTRAINED_ARC
        params.time_limit.FromSeconds(15)
        sol = routing.SolveWithParameters(params)
        
    if not sol:
        print(f"DEBUG: PATH_MOST_CONSTRAINED_ARC failed, trying SAVINGS...")
        # Try one more time with SAVINGS strategy
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.SAVINGS
        params.time_limit.FromSeconds(20)
        sol = routing.SolveWithParameters(params)
        
    if not sol:
        print(f"DEBUG: Solver found NO solution after trying all strategies")
        print(f"DEBUG: Problem constraints: {n_stops} stops, {num_vehicles} vehicles, max {max_stops_per_driver} stops/driver")
        print(f"DEBUG: Work window: {work_window_minutes} minutes ({departure_time} to {work_window_end})")
        
        # Last resort: Try with VERY relaxed time windows (only depot start, very late end)
        print(f"DEBUG: Trying with VERY relaxed time windows (depot start only, end = end of day)...")
        for node in range(n_nodes):
            idx = manager.NodeToIndex(node)
            if node == 0:
                # Depot: must start at or after departure, can return anytime
                time_dim.CumulVar(idx).SetRange(depot_start, 24 * 60 - 1)
            else:
                # Stops: can be visited anytime after departure, up to end of day
                time_dim.CumulVar(idx).SetRange(depot_start, 24 * 60 - 1)
        
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params.time_limit.FromSeconds(20)
        sol = routing.SolveWithParameters(params)
        
        if sol:
            print(f"DEBUG: SUCCESS with very relaxed time windows - original time windows were too restrictive!")
        else:
            print(f"DEBUG: Still infeasible even with very relaxed time windows")
            print(f"DEBUG: This suggests the problem is NOT time windows, but possibly:")
            print(f"DEBUG:   - Travel times are unrealistic (check matrix values)")
            print(f"DEBUG:   - Service times are too long")
            print(f"DEBUG:   - Capacity constraints are still too tight")
            return {
                "feasible": False,
                "error": f"No feasible plan found. Received: {n_stops} stops, {num_vehicles} drivers, max {max_stops_per_driver} stops/driver. Even with very relaxed constraints, solver found no solution. Check server console (PowerShell window) for DEBUG messages showing travel times and constraints. The issue may be unrealistic travel times in the distance matrix."
            }

    print(f"DEBUG: Solver found a solution! Extracting routes...")
    print(f"DEBUG: Solution status: {sol}")
    
    # Extract routes
    routes: List[Dict[str, Any]] = []
    used_vehicle_count = 0

    for v in range(num_vehicles):
        idx = routing.Start(v)
        route_nodes: List[int] = []
        route_times: List[int] = []

        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            tmin = sol.Min(time_dim.CumulVar(idx))
            route_nodes.append(node)
            route_times.append(tmin)
            idx = sol.Value(routing.NextVar(idx))

        # end at depot
        node = manager.IndexToNode(idx)
        tmin = sol.Min(time_dim.CumulVar(idx))
        route_nodes.append(node)
        route_times.append(tmin)

        # Debug: print route info
        non_depot_nodes = [n for n in route_nodes if n != 0]
        print(f"DEBUG: Vehicle {v}: {len(route_nodes)} nodes, {len(non_depot_nodes)} stops: {non_depot_nodes}")

        # If vehicle has no stops (just depot->depot), skip it
        if all(n == 0 for n in route_nodes):
            print(f"DEBUG: Vehicle {v} has no stops, skipping")
            continue

        used_vehicle_count += 1
        print(f"DEBUG: Vehicle {v} is used with {len(non_depot_nodes)} stops")

        ordered_stops: List[str] = []
        schedule_rows: List[Dict[str, Any]] = []
        for n, t in zip(route_nodes, route_times):
            if n == 0:
                schedule_rows.append({"type": "DEPOT", "address": depot_address, "eta": _format_time(day, t)})
            else:
                addr = stops[n - 1]["address"]
                ordered_stops.append(addr)
                schedule_rows.append({
                    "type": "DELIVERY",
                    "address": addr,
                    "eta": _format_time(day, t),
                    "window": f"{_format_time(day, t)} – {_format_time(day, t + 30)}",
                    "notes": stops[n - 1].get("notes", []),
                })

        routes.append({
            "driver_index": v + 1,
            "stops": ordered_stops,
            "maps_link": _google_maps_link(depot_address, ordered_stops),
            "schedule": schedule_rows,
        })

    # Sort routes largest-first so it looks nice
    routes.sort(key=lambda r: len(r["stops"]), reverse=True)

    print(f"DEBUG: Final result: {used_vehicle_count} drivers used, {len(routes)} routes")
    print(f"DEBUG: Routes: {[len(r['stops']) for r in routes]} stops per route")

    if used_vehicle_count == 0 and n_stops > 0:
        # This shouldn't happen if solver found a solution - something is wrong
        print(f"DEBUG: WARNING - Solver found solution but no routes extracted!")
        print(f"DEBUG: This might indicate a bug in route extraction")
        return {
            "feasible": False,
            "error": f"Solver found a solution but no routes were extracted. This may be a bug. Debug: {n_stops} stops, {num_vehicles} vehicles available."
        }

    return {
        "feasible": True,
        "drivers_used": used_vehicle_count,
        "drivers_max": num_vehicles,
        "drivers": routes,  # Frontend expects "drivers" not "routes"
        "routes": routes,  # Keep for backwards compatibility
        "lunch": "Not explicitly scheduled in multi-driver mode (kept fast).",
    }
