"""
Delivery Route Optimizer (K-means clustering + nearest-neighbor).
Handles clustering of delivery stops and route optimization for multiple trucks.
Integrated with the main app; uses GOOGLE_MAPS_API_KEY from config when available.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans

# Optional: googlemaps for real distance/duration when API key is set
try:
    import googlemaps
    _HAS_GOOGLEMAPS = True
except ImportError:
    _HAS_GOOGLEMAPS = False


def _get_api_key() -> str:
    from app import config
    return (getattr(config, "GOOGLE_MAPS_API_KEY", None) or os.getenv("GOOGLE_MAPS_API_KEY", "") or "").strip()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


class DeliveryRouter:
    def __init__(
        self,
        depot_location: Tuple[float, float],
        api_key: Optional[str] = None,
        num_trucks: int = 6,
        max_stops_per_truck: int = 7,
        truck_capacity: float = 2000.0,
    ):
        self.depot = depot_location
        self.num_trucks = num_trucks
        self.max_stops_per_truck = max_stops_per_truck
        self.truck_capacity = truck_capacity
        key = (api_key or _get_api_key()).strip()
        self._use_google = bool(key) and _HAS_GOOGLEMAPS
        self._gmaps = (googlemaps.Client(key=key) if _HAS_GOOGLEMAPS else None) if self._use_google else None

    def cluster_stops(self, stops: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Cluster stops into truck groups using K-means.
        Stops must have 'lat', 'lon'; 'address' and 'id' optional.
        """
        if not stops:
            return {}

        n = len(stops)
        k = min(self.num_trucks, n)
        coords = np.array([[s["lat"], s["lon"]] for s in stops])

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(coords)

        clusters: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(k)}
        for i, stop in enumerate(stops):
            c = int(labels[i])
            clusters[c].append(stop)

        for c in range(k):
            clusters[c].sort(
                key=lambda s: _haversine_km(
                    self.depot[0], self.depot[1], s["lat"], s["lon"]
                )
            )

        clusters = self._balance_clusters(clusters)
        return clusters

    def _get_cluster_gallons(self, stops: List[Dict[str, Any]]) -> float:
        """Calculate total gallons for a cluster of stops."""
        return sum(s.get("gallons", 0) for s in stops)
    
    def _balance_clusters(
        self, clusters: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Balance clusters by both stop count and capacity."""
        max_iterations = 100
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Find overloaded clusters (by stops or capacity)
            overloaded = []
            for k, v in clusters.items():
                total_gallons = self._get_cluster_gallons(v)
                if len(v) > self.max_stops_per_truck or total_gallons > self.truck_capacity:
                    overloaded.append((k, v))
            
            if not overloaded:
                break
            
            truck_id, stops = overloaded[0]
            centroid = self._centroid(stops)
            
            # Find the stop to move (furthest from centroid, or one that reduces capacity overload)
            total_gallons = self._get_cluster_gallons(stops)
            capacity_overload = total_gallons > self.truck_capacity
            
            if capacity_overload:
                # If capacity overloaded, move the stop with most gallons
                furthest_idx = max(
                    range(len(stops)),
                    key=lambda i: stops[i].get("gallons", 0),
                )
            else:
                # If stop count overloaded, move furthest from centroid
                furthest_idx = max(
                    range(len(stops)),
                    key=lambda i: _haversine_km(
                        centroid[0], centroid[1], stops[i]["lat"], stops[i]["lon"]
                    ),
                )
            
            stop_to_move = stops.pop(furthest_idx)

            # Find target cluster (underloaded by stops or capacity)
            underloaded = []
            for k, v in clusters.items():
                if k == truck_id:
                    continue
                total_gallons = self._get_cluster_gallons(v)
                if len(v) < self.max_stops_per_truck and (total_gallons + stop_to_move.get("gallons", 0)) <= self.truck_capacity:
                    underloaded.append((k, v))
            
            if underloaded:
                target = min(
                    underloaded,
                    key=lambda t: _haversine_km(
                        self._centroid(t[1])[0], self._centroid(t[1])[1],
                        stop_to_move["lat"], stop_to_move["lon"],
                    ),
                )[0]
            else:
                # Find cluster with lowest capacity usage
                target = min(
                    [k for k in clusters.keys() if k != truck_id],
                    key=lambda k: (
                        self._get_cluster_gallons(clusters[k]),
                        len(clusters[k])
                    ),
                )

            clusters[target].append(stop_to_move)

        return clusters

    def _centroid(self, stops: List[Dict[str, Any]]) -> Tuple[float, float]:
        if not stops:
            return self.depot
        lats = [s["lat"] for s in stops]
        lons = [s["lon"] for s in stops]
        return (float(np.mean(lats)), float(np.mean(lons)))

    def optimize_route(
        self, stops: List[Dict[str, Any]], use_google_maps: bool = True
    ) -> List[Dict[str, Any]]:
        """Order stops for a single truck. Uses Google when available and requested."""
        if len(stops) <= 1:
            return list(stops)

        use_google = use_google_maps and self._use_google and len(stops) <= 10
        if use_google and self._gmaps:
            out = self._optimize_with_google_maps(stops)
            if out is not None:
                return out
        return self._nearest_neighbor_route(stops)

    def _optimize_with_google_maps(
        self, stops: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        if not self._gmaps or len(stops) > 10:
            return None
        waypoints = [f"{s['lat']},{s['lon']}" for s in stops]
        try:
            directions = self._gmaps.directions(
                origin=f"{self.depot[0]},{self.depot[1]}",
                destination=f"{self.depot[0]},{self.depot[1]}",
                waypoints=waypoints,
                optimize_waypoints=True,
                mode="driving",
            )
            if directions and "waypoint_order" in directions[0]:
                order = directions[0]["waypoint_order"]
                return [stops[i] for i in order]
        except Exception:
            pass
        return None

    def _nearest_neighbor_route(
        self, stops: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        route: List[Dict[str, Any]] = []
        remaining = list(stops)
        curr = self.depot

        while remaining:
            i = min(
                range(len(remaining)),
                key=lambda j: _haversine_km(
                    curr[0], curr[1], remaining[j]["lat"], remaining[j]["lon"]
                ),
            )
            s = remaining.pop(i)
            route.append(s)
            curr = (s["lat"], s["lon"])

        return route

    def get_route_metrics(self, route: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Total distance (km) and duration (min). Uses Google when available."""
        if not route:
            return {"distance_km": 0.0, "duration_min": 0.0, "num_stops": 0}

        if self._use_google and self._gmaps:
            m = self._metrics_google(route)
            if m is not None:
                return m

        # Haversine fallback: assume ~40 km/h average
        total_km = 0.0
        prev = self.depot
        for s in route:
            total_km += _haversine_km(prev[0], prev[1], s["lat"], s["lon"])
            prev = (s["lat"], s["lon"])
        total_km += _haversine_km(prev[0], prev[1], self.depot[0], self.depot[1])
        duration_min = total_km / (40.0 / 60.0) if total_km else 0.0
        return {
            "distance_km": round(total_km, 2),
            "duration_min": round(duration_min, 2),
            "num_stops": len(route),
        }

    def _metrics_google(self, route: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not self._gmaps:
            return None
        waypoints = [f"{self.depot[0]},{self.depot[1]}"]
        waypoints += [f"{s['lat']},{s['lon']}" for s in route]
        waypoints.append(f"{self.depot[0]},{self.depot[1]}")

        total_m = 0.0
        total_s = 0.0
        try:
            for i in range(len(waypoints) - 1):
                r = self._gmaps.distance_matrix(
                    origins=[waypoints[i]],
                    destinations=[waypoints[i + 1]],
                    mode="driving",
                )
                el = r["rows"][0]["elements"][0]
                if el.get("status") == "OK":
                    total_m += el.get("distance", {}).get("value", 0)
                    total_s += el.get("duration", {}).get("value", 0)
            return {
                "distance_km": round(total_m / 1000.0, 2),
                "duration_min": round(total_s / 60.0, 2),
                "num_stops": len(route),
            }
        except Exception:
            return None

    def create_full_routing_plan(
        self,
        stops: List[Dict[str, Any]],
        use_google_optimization: bool = True,
    ) -> Dict[str, Any]:
        """Cluster stops, optimize each truck route, return plan with metrics."""
        clusters = self.cluster_stops(stops)
        plan: Dict[str, Any] = {}

        for truck_id, truck_stops in clusters.items():
            # Validate capacity before optimizing
            total_gallons = self._get_cluster_gallons(truck_stops)
            if total_gallons > self.truck_capacity:
                # This shouldn't happen after balancing, but handle it gracefully
                # Try to remove stops until capacity is met
                truck_stops_sorted = sorted(truck_stops, key=lambda s: s.get("gallons", 0), reverse=True)
                valid_stops = []
                current_gallons = 0
                for stop in truck_stops_sorted:
                    stop_gallons = stop.get("gallons", 0)
                    if current_gallons + stop_gallons <= self.truck_capacity:
                        valid_stops.append(stop)
                        current_gallons += stop_gallons
                truck_stops = valid_stops
            
            ordered = self.optimize_route(truck_stops, use_google_maps=use_google_optimization)
            metrics = self.get_route_metrics(ordered)
            plan[f"Truck_{truck_id + 1}"] = {
                "stops": ordered,
                "metrics": metrics,
                "stop_count": len(ordered),
                "total_gallons": self._get_cluster_gallons(ordered),
            }

        total_km = sum(p["metrics"]["distance_km"] for p in plan.values())
        total_min = sum(p["metrics"]["duration_min"] for p in plan.values())
        plan["summary"] = {
            "total_distance_km": total_km,
            "total_duration_min": total_min,
            "num_trucks": len(clusters),
            "total_stops": len(stops),
        }
        return plan
