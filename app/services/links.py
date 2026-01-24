from typing import List, Optional, Tuple
from urllib.parse import urlencode


def maps_dir_url(origin: str, destination: str, waypoints: List[str]) -> str:
    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": "driving",
    }
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def chunked_links(depot: str, ordered_stops: List[str]) -> List[str]:
    """Create mobile-safe links (<=3 waypoints per link).

    For 8 stops, we create:
      Leg 1: depot -> stop4 with waypoints stop1-3
      Leg 2: stop4 -> stop8 with waypoints stop5-7
      Leg 3: stop8 -> depot
    """
    s = ordered_stops
    links = []
    if len(s) >= 4:
        links.append(maps_dir_url(depot, s[3], s[0:3]))
    if len(s) >= 8:
        links.append(maps_dir_url(s[3], s[7], s[4:7]))
    if s:
        links.append(maps_dir_url(s[-1], depot, []))
    return links


def multi_stop_link(
    depot: str,
    ordered_stops: List[str],
    depot_coords: Optional[Tuple[float, float]] = None,
    stop_coords: Optional[List[Tuple[float, float]]] = None,
) -> str:
    """Create a Google Maps directions link: depot → stops → depot (round trip).

    Uses origin=depot, destination=depot, waypoints=all stops so each truck
    returns to depot at the end. Prefers lat,lon when provided for reliable routing.
    """
    if not ordered_stops:
        return "https://www.google.com/maps/search/?api=1&query=" + str(depot)

    use_coords = (
        depot_coords is not None
        and stop_coords is not None
        and len(stop_coords) == len(ordered_stops)
    )
    if use_coords:
        origin = f"{depot_coords[0]},{depot_coords[1]}"
        dest_str = origin
        way_strs = [f"{c[0]},{c[1]}" for c in stop_coords]
    else:
        origin = depot
        dest_str = depot
        way_strs = list(ordered_stops)

    return maps_dir_url(origin, dest_str, way_strs)
