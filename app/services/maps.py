from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

GOOGLE_ROUTES_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

# Google limit: origins * destinations <= 625
# 25*25 = 625 (max safe chunk)
CHUNK = 25

# If Google cannot route a pair, we fill with a large penalty so the solver avoids it.
UNROUTABLE_PENALTY_SECONDS = 6 * 60 * 60  # 6 hours


def has_google_key() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_API_KEY", "").strip())


def _synthetic_matrix_seconds(nodes: List[str]) -> Tuple[List[List[int]], Dict[str, Any]]:
    # Deterministic synthetic travel times; keeps app usable without Google.
    n = len(nodes)
    m = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                m[i][j] = 0
            else:
                d = abs(i - j)
                m[i][j] = 6 * 60 + d * 4 * 60  # base 6 min + 4 min per index step
    meta = {
        "source": "synthetic",
        "note": "Google Routes API not configured; using deterministic synthetic travel times.",
    }
    return m, meta


def _parse_duration_seconds(duration: Any) -> Optional[int]:
    # Google returns duration like "123s"
    if duration is None:
        return None
    if isinstance(duration, str) and duration.endswith("s"):
        try:
            return int(float(duration[:-1]))
        except Exception:
            return None
    return None


async def _google_matrix_chunk(
    client: httpx.AsyncClient,
    origins: List[str],
    destinations: List[str],
    origin_offset: int,
    dest_offset: int,
    out_matrix: List[List[int]],
    bad_pairs: List[Dict[str, Any]],
) -> None:
    payload = {
        "origins": [{"waypoint": {"address": a}} for a in origins],
        "destinations": [{"waypoint": {"address": a}} for a in destinations],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }

    headers = {
        "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_API_KEY", "").strip(),
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,status,condition",
        "Content-Type": "application/json",
    }

    # Basic retry for transient errors
    last_status = None
    last_text = None

    for attempt in range(4):
        resp = await client.post(GOOGLE_ROUTES_MATRIX_URL, json=payload, headers=headers, timeout=60.0)
        last_status = resp.status_code
        last_text = resp.text

        if resp.status_code == 200:
            data = resp.json()  # list of elements

            for el in data:
                oi = el.get("originIndex")
                di = el.get("destinationIndex")
                status = el.get("status")
                condition = el.get("condition")
                dur = _parse_duration_seconds(el.get("duration"))

                if oi is None or di is None:
                    continue

                i = origin_offset + int(oi)
                j = dest_offset + int(di)

                if status == "OK" and dur is not None and (condition is None or condition == "ROUTE_EXISTS"):
                    out_matrix[i][j] = max(0, int(dur))
                else:
                    out_matrix[i][j] = UNROUTABLE_PENALTY_SECONDS
                    bad_pairs.append(
                        {
                            "origin": origins[int(oi)] if int(oi) < len(origins) else None,
                            "destination": destinations[int(di)] if int(di) < len(destinations) else None,
                            "status": status,
                            "condition": condition,
                        }
                    )
            return

        if resp.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(0.5 * (2**attempt))
            continue

        raise RuntimeError(f"Google computeRouteMatrix failed: {resp.status_code} {resp.text}")

    raise RuntimeError(f"Google computeRouteMatrix failed after retries: {last_status} {last_text}")


async def compute_matrix_seconds(nodes: List[str]) -> Tuple[List[List[int]], Dict[str, Any]]:
    """
    Returns (matrix_seconds, meta)
    matrix_seconds is NxN, where N=len(nodes)

    Uses Google Routes API if GOOGLE_MAPS_API_KEY is set; otherwise synthetic.
    Batches calls to respect origins*destinations <= 625.
    """
    n = len(nodes)
    if n == 0:
        return [], {"source": "synthetic", "note": "No nodes"}

    # Start with full penalty matrix; set diagonal to 0
    matrix = [[UNROUTABLE_PENALTY_SECONDS for _ in range(n)] for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 0

    if not has_google_key():
        return _synthetic_matrix_seconds(nodes)

    bad_pairs: List[Dict[str, Any]] = []
    calls = 0

    try:
        async with httpx.AsyncClient() as client:
            for i0 in range(0, n, CHUNK):
                origins = nodes[i0 : i0 + CHUNK]
                for j0 in range(0, n, CHUNK):
                    destinations = nodes[j0 : j0 + CHUNK]
                    calls += 1
                    await _google_matrix_chunk(
                        client=client,
                        origins=origins,
                        destinations=destinations,
                        origin_offset=i0,
                        dest_offset=j0,
                        out_matrix=matrix,
                        bad_pairs=bad_pairs,
                    )

        meta = {
            "source": "google",
            "note": f"Google Routes computeRouteMatrix used with batching (chunk={CHUNK}).",
            "calls": calls,
            "bad_pairs": bad_pairs[:50],
            "bad_pairs_count": len(bad_pairs),
        }
        return matrix, meta

    except Exception as e:
        synth, meta = _synthetic_matrix_seconds(nodes)
        meta.update(
            {
                "source": "synthetic",
                "note": "Google Routes API failed; using deterministic synthetic travel times.",
                "google_error": str(e),
            }
        )
        return synth, meta


# --- Backwards-compatible alias (so older main.py imports still work) ---
async def compute_route_matrix(nodes: List[str]) -> Tuple[List[List[int]], Dict[str, Any]]:
    return await compute_matrix_seconds(nodes)


# --- Geocoding (address → lat, lon) for cluster-from-addresses ---
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for an address, or None if missing key or geocode fails."""
    key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not key:
        return None
    addr = (address or "").strip()
    if not addr:
        return None
    import urllib.parse
    params = {"address": addr, "key": key}
    url = GEOCODE_URL + "?" + urllib.parse.urlencode(params)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
            if r.status_code != 200:
                return None
            data = r.json()
            results = data.get("results") or []
            if not results:
                return None
            loc = results[0].get("geometry", {}).get("location")
            if not loc:
                return None
            return (float(loc["lat"]), float(loc["lng"]))
    except Exception:
        return None


async def geocode_addresses(addresses: List[str]) -> List[Dict[str, Any]]:
    """Geocode each address; return [{address, lat, lon}, ...] for successful geocodes."""
    out: List[Dict[str, Any]] = []
    for i, addr in enumerate(addresses):
        t = await geocode_address(addr)
        if t is None:
            continue
        out.append({"id": i + 1, "address": addr.strip(), "lat": t[0], "lon": t[1]})
    return out
