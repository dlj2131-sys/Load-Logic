from typing import List
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


def multi_stop_link(depot: str, ordered_stops: List[str]) -> str:
    """Create a single multi-stop Google Maps directions link.

    NOTE: Google Maps URL waypoint limits vary by platform; this function intentionally
    creates a single link as requested.
    """
    return maps_dir_url(depot, depot, ordered_stops)
