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

from app.services.maps import compute_matrix_seconds, has_google_key
from app.services.multi_planner import plan_multi_routes

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def api_health() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "has_google_key": has_google_key(),
            "default_departure": "07:00",
        },
    )


def _split_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in (text or "").splitlines()]
    cleaned: List[str] = []
    for ln in lines:
        if not ln:
            continue
        # remove leading "12." or "12)" etc
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
