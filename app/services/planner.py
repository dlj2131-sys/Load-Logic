from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional, Tuple

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

ET = ZoneInfo("America/New_York")


@dataclass
class Stop:
    address: str
    service_minutes: int
    notes: List[str]
    window_start: Optional[str] = None  # HH:MM
    window_end: Optional[str] = None    # HH:MM


def _parse_hhmm(day: datetime, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return day.replace(hour=h, minute=m, second=0, microsecond=0)


def _min_of_day(dt: datetime) -> int:
    day0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int((dt - day0).total_seconds() // 60)


def _format_time(day: datetime, minutes_since_midnight: int) -> str:
    dt = day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=minutes_since_midnight)
    # portable 12-hour format (Windows may not like %-I)
    return dt.strftime("%I:%M %p").lstrip("0")


def _solve_once(
    depot_address: str,
    stops: List[Stop],
    durations_seconds: List[List[float]],
    date_yyyy_mm_dd: str,
    departure_time: str,
    work_window_start: str,
    work_window_end: str,
    lunch_window_start: str,
    lunch_window_end: str,
    lunch_minutes: int,
    use_lunch: bool,
) -> Dict[str, Any]:
    # Nodes: 0 = depot(start), 1..N = deliveries, N+1 = depot(return)
    n_deliv = len(stops)
    n_nodes = n_deliv + 2

    # Convert seconds -> minutes int
    def sec_to_min(x: float) -> int:
        if x > 1e8:
            return int(x)
        return max(0, int(round(x / 60.0)))

    travel = [[sec_to_min(durations_seconds[i][j]) for j in range(n_nodes)] for i in range(n_nodes)]
    service = [0] + [max(0, int(s.service_minutes)) for s in stops] + [0]

    day = datetime.fromisoformat(date_yyyy_mm_dd).replace(tzinfo=ET)
    depart_dt = _parse_hhmm(day, departure_time)
    open_dt = _parse_hhmm(day, work_window_start)
    close_dt = _parse_hhmm(day, work_window_end)

    # Time windows per node
    tw: List[Tuple[int, int]] = []
    tw.append((_min_of_day(depart_dt), _min_of_day(close_dt)))  # start depot

    for s in stops:
        ws = _parse_hhmm(day, s.window_start) if s.window_start else open_dt
        we = _parse_hhmm(day, s.window_end) if s.window_end else close_dt
        tw.append((_min_of_day(ws), _min_of_day(we)))

    # Return depot window (allow later return if needed; adjust if you want a hard return time)
    return_latest = _min_of_day(close_dt) + 180  # 3 hr grace
    tw.append((_min_of_day(depart_dt), min(24 * 60 - 1, return_latest)))

    # IMPORTANT: recent OR-Tools expects (starts, ends) as lists for a single vehicle
    manager = pywrapcp.RoutingIndexManager(n_nodes, 1, [0], [n_nodes - 1])
    routing = pywrapcp.RoutingModel(manager)

    def transit_cb(from_index: int, to_index: int) -> int:
        frm = manager.IndexToNode(from_index)
        to = manager.IndexToNode(to_index)
        return travel[frm][to] + service[frm]

    transit_idx = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # Time dimension with waiting slack
    horizon = 24 * 60
    routing.AddDimension(
        transit_idx,
        60,      # waiting slack (minutes)
        horizon, # horizon
        False,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Apply time windows
    for node in range(n_nodes):
        idx = manager.NodeToIndex(node)
        a, b = tw[node]
        time_dim.CumulVar(idx).SetRange(a, b)

    # Optional lunch break
    if use_lunch and lunch_minutes > 0:
        solver = routing.solver()
        l_start = _min_of_day(_parse_hhmm(day, lunch_window_start))
        l_end = _min_of_day(_parse_hhmm(day, lunch_window_end))
        lunch = solver.FixedDurationIntervalVar(l_start, l_end, int(lunch_minutes), False, "lunch")
        time_dim.SetBreakIntervalsOfVehicle([lunch], 0)

    # Search parameters
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    # Guided local search helps a bit, but keep time bound tight for responsiveness
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(5)

    sol = routing.SolveWithParameters(params)
    if not sol:
        return {"feasible": False}

    # Extract route order with times
    index = routing.Start(0)
    visit_nodes: List[int] = []
    visit_times: List[int] = []
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        t = sol.Min(time_dim.CumulVar(index))
        visit_nodes.append(node)
        visit_times.append(t)
        index = sol.Value(routing.NextVar(index))
    # end
    node = manager.IndexToNode(index)
    t = sol.Min(time_dim.CumulVar(index))
    visit_nodes.append(node)
    visit_times.append(t)

    # Build schedule
    schedule = []
    delivery_addresses = []
    for node, tmin in zip(visit_nodes, visit_times):
        if node == 0:
            schedule.append({"type": "DEPOT_START", "address": depot_address, "eta": _format_time(day, tmin)})
        elif node == n_nodes - 1:
            schedule.append({"type": "DEPOT_RETURN", "address": depot_address, "eta": _format_time(day, tmin)})
        else:
            s = stops[node - 1]
            eta = _format_time(day, tmin)
            window = f"{eta} – {_format_time(day, tmin + 30)}"
            schedule.append(
                {
                    "type": "DELIVERY",
                    "address": s.address,
                    "eta": eta,
                    "window": window,
                    "notes": s.notes,
                }
            )
            delivery_addresses.append(s.address)

    return {
        "feasible": True,
        "schedule": schedule,
        "ordered_deliveries": delivery_addresses,
        "return_eta": schedule[-1]["eta"],
    }


def plan_route(
    depot_address: str,
    stops: List[Stop],
    durations_seconds: List[List[float]],
    date_yyyy_mm_dd: str,
    departure_time: str,
    work_window_start: str,
    work_window_end: str,
    lunch_window_start: str,
    lunch_window_end: str,
    lunch_minutes: int,
    lunch_skippable: bool,
) -> Dict[str, Any]:
    # First try with lunch; if infeasible and skippable, retry without.
    r = _solve_once(
        depot_address=depot_address,
        stops=stops,
        durations_seconds=durations_seconds,
        date_yyyy_mm_dd=date_yyyy_mm_dd,
        departure_time=departure_time,
        work_window_start=work_window_start,
        work_window_end=work_window_end,
        lunch_window_start=lunch_window_start,
        lunch_window_end=lunch_window_end,
        lunch_minutes=lunch_minutes,
        use_lunch=True,
    )
    if r.get("feasible"):
        r["lunch"] = "Scheduled (solver placed a lunch break if possible)"
        return r

    if lunch_skippable:
        r2 = _solve_once(
            depot_address=depot_address,
            stops=stops,
            durations_seconds=durations_seconds,
            date_yyyy_mm_dd=date_yyyy_mm_dd,
            departure_time=departure_time,
            work_window_start=work_window_start,
            work_window_end=work_window_end,
            lunch_window_start=lunch_window_start,
            lunch_window_end=lunch_window_end,
            lunch_minutes=lunch_minutes,
            use_lunch=False,
        )
        if r2.get("feasible"):
            r2["lunch"] = "Skipped (needed for feasibility)"
        return r2

    r["lunch"] = "No feasible route with required lunch"
    return r
