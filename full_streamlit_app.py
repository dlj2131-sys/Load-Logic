"""
Load Logic - Full Route Planning System (Streamlit)
Route Planner, Requests, Book, Dashboard — no backend API required.
"""

import streamlit as st
import sys
import os
from typing import List, Dict, Any, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    if hasattr(st, "secrets") and "GOOGLE_MAPS_API_KEY" in st.secrets:
        os.environ["GOOGLE_MAPS_API_KEY"] = st.secrets["GOOGLE_MAPS_API_KEY"]
except Exception:
    pass

try:
    import app.config  # noqa: F401
except Exception:
    pass

from app.services.maps import geocode_address, has_google_key
from app.services.delivery_router import DeliveryRouter
from app.services.links import multi_stop_link
from app.db import requests_repo, drivers_repo, routes_repo

st.set_page_config(
    page_title="Load Logic - Route Planning System",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session state
if "stops" not in st.session_state:
    st.session_state.stops = [{"address": "", "gallons": 0}]
if "selected_request_ids" not in st.session_state:
    st.session_state.selected_request_ids = []


def _has_api_key() -> bool:
    return has_google_key()


def geocode_address_sync(address: str) -> Optional[Tuple[float, float]]:
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    try:
        return asyncio.run(geocode_address(address))
    except Exception as e:
        if "st" in dir():
            st.warning(f"Geocoding error: {str(e)}")
        return None


def parse_coordinates(coord_str: str) -> Optional[Tuple[float, float]]:
    try:
        parts = coord_str.strip().split(",")
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
    except (ValueError, AttributeError):
        pass
    return None


def is_coordinate_string(s: str) -> bool:
    s = (s or "").strip()
    if "," in s:
        parts = s.split(",")
        if len(parts) == 2:
            try:
                float(parts[0].strip())
                float(parts[1].strip())
                return True
            except ValueError:
                pass
    return False


# ---- Sidebar: navigation ----
with st.sidebar:
    st.markdown("### 🚛 Load Logic")
    st.markdown("**Route Planning System**")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Route Planner", "Requests", "Book", "Dashboard"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    if _has_api_key():
        st.success("✅ Google Maps API")
    else:
        st.warning("⚠️ No API key – use coordinates")

# ---- Route Planner ----
def render_route_planner():
    st.header("🗺️ Route Planner")
    st.markdown("Plan optimized delivery routes with capacity constraints.")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### ⚙️ Route settings")
        max_drivers = st.number_input("Max drivers", 1, 20, 6, key="rp_max_drivers")
        max_stops_per_driver = st.number_input("Max stops per driver", 1, 20, 7, key="rp_max_stops")
        truck_capacity = st.number_input("Truck capacity (gal)", 100, 10000, 2000, 100, key="rp_capacity")

    with st.form("route_planner_form", clear_on_submit=False):
        depot_input = st.text_area("Depot address or coordinates", placeholder="123 Depot Rd or 40.7128,-74.0060", height=60)
        st.markdown("**Customer stops**")
        removed_idx = None
        for i, stop in enumerate(st.session_state.stops):
            c1, c2, c3 = st.columns([4, 1, 0.5])
            with c1:
                st.session_state.stops[i]["address"] = st.text_input(f"Stop {i+1}", value=stop.get("address", ""), key=f"stop_a_{i}", placeholder="Address or lat,lon")
            with c2:
                st.session_state.stops[i]["gallons"] = st.number_input("Gal", 0, 10000, int(stop.get("gallons", 0)), key=f"stop_g_{i}")
            with c3:
                if st.form_submit_button("🗑️", key=f"del_{i}"):
                    removed_idx = i
        add_clicked = st.form_submit_button("➕ Add stop")
        submitted = st.form_submit_button("🚗 Plan routes")

    if add_clicked:
        st.session_state.stops.append({"address": "", "gallons": 0})
        st.rerun()
    if removed_idx is not None and len(st.session_state.stops) > 1:
        st.session_state.stops.pop(removed_idx)
        st.rerun()

    if submitted:
        if not depot_input.strip():
            st.error("Enter depot address or coordinates.")
            return
        valid = [s for s in st.session_state.stops if (s.get("address") or "").strip()]
        if not valid:
            st.error("Add at least one stop.")
            return
        if len(valid) > 50:
            st.error("Max 50 stops.")
            return

        with st.spinner("Planning…"):
            depot_coords = None
            depot_display = depot_input.strip()
            if is_coordinate_string(depot_input):
                depot_coords = parse_coordinates(depot_input)
                if not depot_coords:
                    st.error("Invalid depot coordinates.")
                    return
            else:
                if not _has_api_key():
                    st.error("Geocoding requires GOOGLE_MAPS_API_KEY. Use coordinates.")
                    return
                depot_coords = geocode_address_sync(depot_input.strip())
                if not depot_coords:
                    st.error("Could not geocode depot.")
                    return

            processed = []
            for i, s in enumerate(valid):
                addr = (s.get("address") or "").strip()
                g = float(s.get("gallons", 0) or 0)
                if is_coordinate_string(addr):
                    coords = parse_coordinates(addr)
                    if coords:
                        processed.append({"id": i + 1, "address": addr, "lat": coords[0], "lon": coords[1], "gallons": g})
                elif _has_api_key():
                    geo = geocode_address_sync(addr)
                    if geo:
                        processed.append({"id": i + 1, "address": addr, "lat": geo[0], "lon": geo[1], "gallons": g})
                    else:
                        st.warning(f"Could not geocode: {addr}")
                else:
                    st.error("Use coordinates or set API key.")
                    return

            if not processed:
                st.error("No valid stops.")
                return

            router = DeliveryRouter(depot_coords, num_trucks=max_drivers, max_stops_per_truck=max_stops_per_driver, truck_capacity=truck_capacity)
            plan = router.create_full_routing_plan(processed, use_google_optimization=_has_api_key())

            st.success(f"✅ {len([k for k in plan if k != 'summary'])} route(s)")
            for key in sorted(plan.keys()):
                if key == "summary":
                    continue
                truck = plan.get(key)
                if not isinstance(truck, dict):
                    continue
                stops_list = truck.get("stops") or []
                if not stops_list:
                    continue
                addrs = []
                total_g = 0
                for s in stops_list:
                    a = s.get("address") or (f"{s['lat']},{s['lon']}" if "lat" in s else "")
                    if a:
                        addrs.append(a)
                    total_g += float(s.get("gallons", 0))
                if not addrs:
                    continue
                link = multi_stop_link(depot_display, addrs)
                with st.expander(f"🚛 {key.replace('_', ' ')} — {len(stops_list)} stops, {total_g:.0f} gal", expanded=True):
                    st.markdown(f"[🗺️ Google Maps]({link})")
                    for j, a in enumerate(addrs, 1):
                        st.markdown(f"{j}. {a}")


# ---- Requests ----
def render_requests():
    st.header("📋 Requests")
    st.markdown("Delivery requests. Select for batching on the Dashboard.")

    status_filter = st.selectbox("Filter", ["all", "pending", "assigned", "completed", "cancelled"], key="req_filter")
    status = None if status_filter == "all" else status_filter
    requests_list = requests_repo.list_requests(status=status)

    if not requests_list:
        st.info("No requests. Use **Book** to add one.")
        return

    for r in requests_list:
        addr_short = (r.delivery_address[:50] + "…") if len(r.delivery_address) > 50 else r.delivery_address
        sel = st.checkbox(
            f"**{r.id}** — {addr_short} — `{r.status}`",
            value=r.id in st.session_state.selected_request_ids,
            key=f"sel_{r.id}",
        )
        if sel and r.id not in st.session_state.selected_request_ids:
            st.session_state.selected_request_ids.append(r.id)
        elif not sel and r.id in st.session_state.selected_request_ids:
            st.session_state.selected_request_ids.remove(r.id)
        with st.expander("Details", expanded=False):
            st.markdown(f"**{r.customer_name}** · {r.customer_email} · {r.customer_phone}")
            st.markdown(f"Address: {r.delivery_address}")
            st.markdown(f"Gallons: {r.order_quantity_gallons} · Priority: {r.delivery_priority}")


# ---- Book ----
def render_book():
    st.header("📦 Book")
    st.markdown("Submit a delivery request.")

    with st.form("book_form"):
        name = st.text_input("Customer name *")
        email = st.text_input("Email *")
        phone = st.text_input("Phone *")
        address = st.text_area("Delivery address *")
        fuel = st.selectbox("Fuel type", ["Heating Oil", "Diesel", "Kerosene", "Other"], key="fuel")
        tank_loc = st.text_input("Tank location", placeholder="e.g. Basement")
        gallons = st.number_input("Order quantity (gallons)", 0.0, 5000.0, 275.0, 25.0)
        tank_empty = st.checkbox("Tank empty")
        priority = st.selectbox("Priority", ["Standard", "Rush", "Emergency"], key="priority")
        notes = st.text_area("Special considerations", placeholder="Optional")
        pay = st.selectbox("Payment", ["Credit Card", "Check", "Cash", "Other"], key="pay")
        submitted = st.form_submit_button("Submit booking")

    if submitted:
        if not all([name, email, phone, address]):
            st.error("Fill required fields: name, email, phone, address.")
            return
        lat, lon = None, None
        if _has_api_key():
            geo = geocode_address_sync(address.strip())
            if not geo:
                st.error("Could not geocode address. Check it or set GOOGLE_MAPS_API_KEY.")
                return
            lat, lon = geo
        else:
            st.warning("No API key — request saved but without coordinates. It won’t be used for routing until geocoded.")

        try:
            req = requests_repo.create_request(
                customer_name=name.strip(),
                customer_email=email.strip(),
                customer_phone=phone.strip(),
                delivery_address=address.strip(),
                lat=lat,
                lon=lon,
                fuel_type=fuel,
                heating_unit_type="Furnace",
                tank_location=tank_loc or "",
                access_instructions=None,
                current_tank_level="Unknown",
                order_quantity_gallons=gallons,
                tank_empty=tank_empty,
                requested_delivery_date=None,
                delivery_priority=priority,
                special_considerations=notes or None,
                payment_method=pay,
            )
            st.success(f"✅ Request {req.id} created. Track at `/customer/track/{req.id}`")
        except Exception as e:
            st.error(str(e))


# ---- Dashboard (batch to routes) ----
def render_dashboard():
    st.header("📊 Dashboard")
    st.markdown("Create driver routes from selected pending requests.")

    pending = [r for r in requests_repo.list_requests(status="pending") if r.lat is not None and r.lon is not None]
    drivers = drivers_repo.get_all_drivers()

    if not drivers:
        st.warning("No drivers in `data/drivers.json`. Add drivers first.")
        return
    if not pending:
        st.info("No pending requests with coordinates. Use **Book** (with API key) to add geocoded requests.")
        return

    # Use selected IDs; default to all pending
    eligible_ids = {r.id for r in pending}
    selected = set(st.session_state.selected_request_ids) & eligible_ids
    if not selected:
        selected = eligible_ids

    st.markdown(f"**{len(selected)}** request(s) selected for routing.")
    depot = st.text_input("Depot address *", placeholder="123 Depot Rd or 40.7128,-74.0060", key="dash_depot")
    max_d = st.number_input("Max drivers", 1, 20, min(len(drivers), 6), key="dash_max_drivers")
    max_s = st.number_input("Max stops per driver", 1, 20, 7, key="dash_max_stops")

    if st.button("Create routes from selected"):
        if not depot.strip():
            st.error("Enter depot address.")
            return
        all_reqs = {r.id: r for r in requests_repo.list_requests()}
        selected_reqs = [all_reqs[rid] for rid in selected if rid in all_reqs and all_reqs[rid].lat and all_reqs[rid].lon]
        if not selected_reqs:
            st.error("No selected requests have coordinates.")
            return

        stops_fc = []
        req_map = {}
        for r in selected_reqs:
            sid = f"stop_{r.id}"
            stops_fc.append({"id": sid, "lat": r.lat, "lon": r.lon, "address": r.delivery_address})
            req_map[sid] = r

        if _has_api_key():
            dep_coords = geocode_address_sync(depot.strip())
            if not dep_coords:
                st.error("Could not geocode depot.")
                return
            depot_loc = dep_coords
            depot_str = depot.strip()
        else:
            depot_loc = (40.7589, -73.9851)
            depot_str = "40.7589,-73.9851"

        router = DeliveryRouter(depot_loc, num_trucks=min(max_d, len(drivers)), max_stops_per_truck=max_s)
        clusters = router.cluster_stops(stops_fc)
        created = []
        driver_list = drivers[: len(clusters)]

        for i, (cid, cstops) in enumerate(clusters.items()):
            if i >= len(driver_list):
                break
            drv = driver_list[i]
            ordered = router.optimize_route(cstops, use_google_maps=_has_api_key())
            ordered_ids = [s["id"] for s in ordered]
            enriched = []
            for s in ordered:
                r = req_map.get(s["id"])
                if r:
                    enriched.append({
                        "id": r.id,
                        "address": r.delivery_address,
                        "lat": r.lat,
                        "lon": r.lon,
                        "service_minutes": 20,
                        "access_instructions": r.access_instructions,
                        "gate_code": None,
                        "tank_location": r.tank_location,
                        "customer_notes": r.special_considerations,
                        "payment_required": False,
                    })
            addrs = [e["address"] for e in enriched]
            link = multi_stop_link(depot_str, addrs)
            route = routes_repo.create_route(
                driver_id=drv.id,
                depot={"lat": depot_loc[0], "lon": depot_loc[1]},
                stops=enriched,
                ordered_deliveries=[e["id"] for e in enriched],
                google_maps_link=link,
                feasible=True,
            )
            for e in enriched:
                requests_repo.assign_to_route(e["id"], route.id)
            created.append({"route_id": route.id, "driver": drv.name, "stops": len(enriched)})

        st.success(f"✅ Created {len(created)} route(s)")
        for x in created:
            st.markdown(f"- **{x['driver']}**: {x['stops']} stops — route `{x['route_id']}`")
        for r in selected_reqs:
            if r.id in st.session_state.selected_request_ids:
                st.session_state.selected_request_ids.remove(r.id)


# ---- Main ----
if page == "Route Planner":
    render_route_planner()
elif page == "Requests":
    render_requests()
elif page == "Book":
    render_book()
else:
    render_dashboard()
