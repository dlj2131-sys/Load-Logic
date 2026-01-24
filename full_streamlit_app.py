"""
Load Logic - Route Planning & Delivery (Streamlit)
Landing → Submit order (Book) | Admin Portal (Dashboard → Route Planner, Requests).
"""

import streamlit as st
import sys
import os
from typing import List, Dict, Any, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import app.config  # noqa: F401
except Exception:
    pass

from app.services.maps import geocode_address, has_google_key
from app.services.delivery_router import DeliveryRouter
from app.services.links import multi_stop_link
from app.db import requests_repo, drivers_repo, routes_repo

DEFAULT_DEPOT = "7 Lush Lane, New Windsor, NY 12553"

st.set_page_config(
    page_title="Load Logic — Heating Oil Delivery",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Page state ----
if "page" not in st.session_state:
    st.session_state.page = "landing"
if "stops" not in st.session_state:
    st.session_state.stops = [{"address": "", "gallons": 0}]
if "selected_request_ids" not in st.session_state:
    st.session_state.selected_request_ids = []

# Nav via query param (for header links overlaid on banner)
_valid_pages = ("landing", "book", "dashboard", "route_planner", "requests")
_qp = st.query_params.get("page")
if _qp in _valid_pages and _qp != st.session_state.page:
    st.session_state.page = _qp
    try:
        del st.query_params["page"]
    except Exception:
        pass
    st.rerun()

page = st.session_state.page

# ---- CSS (website-style, hide sidebar on landing/book) ----
SITE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; font-size: 16px; }
h1, h2, h3 { font-family: 'Libre Baskerville', serif !important; color: #991b1b !important; font-weight: 700 !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { font-family: 'Libre Baskerville', serif !important; color: #991b1b !important; font-weight: 700 !important; }
.stMarkdown p { font-size: 1.05rem !important; line-height: 1.5 !important; }

.stApp { background: linear-gradient(180deg, #fef2f2 0%, #fee2e2 100%); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #b91c1c 0%, #991b1b 50%, #7f1d1d 100%) !important; }
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio label, [data-testid="stSidebar"] .stRadio * { color: #fff !important; font-size: 1.05rem !important; font-weight: 600 !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #fecaca !important; }
[data-testid="stSidebar"] [data-testid="stAlert"], [data-testid="stSidebar"] [data-baseweb="notification"] { font-size: 0.95rem !important; font-weight: 700 !important; }

.stButton > button, [data-testid="stForm"] button { background: #dc2626 !important; color: #fff !important; font-weight: 700 !important;
  border: none !important; border-radius: 6px !important; padding: 0.5rem 1.25rem !important;
  white-space: nowrap !important; }
.stButton > button:hover, [data-testid="stForm"] button:hover { background: #b91c1c !important; color: #fff !important; }

[data-testid="stExpander"] { background: #fff !important; border: 1px solid #fecaca !important; border-radius: 8px !important; }
.streamlit-expanderHeader { background: #fee2e2 !important; font-weight: 600 !important; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, textarea { border: 1px solid #fecaca !important; border-radius: 6px !important; }
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus, textarea:focus { border-color: #991b1b !important; box-shadow: 0 0 0 2px rgba(153,27,27,0.25) !important; }

.brand-hero { background: linear-gradient(135deg, #b91c1c 0%, #991b1b 50%, #7f1d1d 100%); color: #fff; padding: 1.5rem 2rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 4px solid #fca5a5; }
.brand-hero .logo { font-family: 'Libre Baskerville', serif; font-size: 1.75rem; font-weight: 700; }
.brand-hero .est { font-size: 1rem; opacity: .95; margin-left: .5rem; font-weight: 600; }
.brand-hero .tagline { font-size: 1.1rem; margin-top: .4rem; opacity: .98; }

/* Header: faded bg with nav links overlaid */
.header-wrap { position: relative; width: 100%; min-height: 100px; background-size: cover !important;
  background-position: center !important; background-repeat: no-repeat !important; margin-bottom: 1rem;
  border-radius: 8px; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0.5rem 1rem; }
.header-nav { display: flex; flex-direction: column; align-items: flex-end; gap: 0.35rem; }
.header-nav a { display: inline-block; padding: 0.5rem 1.25rem; background: #dc2626; color: #fff !important;
  font-weight: 700; text-decoration: none; border-radius: 6px; font-size: 0.95rem; white-space: nowrap;
  border: none; transition: background 0.2s; }
.header-nav a:hover { background: #b91c1c; color: #fff !important; }
.nav-wrap { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
  padding: 0.75rem 0; margin-bottom: 1.5rem; border-bottom: 2px solid #fecaca; }
.nav-left { display: flex; align-items: center; gap: 1rem; }
.nav-right { display: flex; align-items: center; gap: 0.75rem; }
.nav-logo { font-family: 'Libre Baskerville', serif; font-size: 1.4rem; font-weight: 700; color: #991b1b; }
[data-testid="stCaptionContainer"] { color: #64748b !important; font-size: 0.95rem !important; }
[data-testid="stAlert"], [data-baseweb="notification"] { font-size: 1.05rem !important; font-weight: 700 !important; }
</style>
"""
st.markdown(SITE_CSS, unsafe_allow_html=True)

# Hide sidebar everywhere (nav is in main header + dashboard buttons)
st.markdown("""
<style>
[data-testid="stSidebar"], section[data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# Header: faded bg image with nav links overlaid (query params for nav)
_header_bg_path = os.path.join(os.path.dirname(__file__), "app", "static", "images", "header_bg.png")
if os.path.isfile(_header_bg_path):
    import base64
    with open(_header_bg_path, "rb") as _f:
        _b64 = base64.b64encode(_f.read()).decode()
    _data_url = f"data:image/png;base64,{_b64}"
    _home = '' if page == 'landing' else '<a href="?page=landing">Home</a>'
    _nav_html = f'''
    <div class="header-nav">
      {_home}
      <a href="?page=book">Submit an order</a>
      <a href="?page=dashboard">Admin Portal</a>
    </div>'''
    st.markdown(f'''
    <style>
    .header-wrap {{ background-image: linear-gradient(to right, rgba(254,242,242,0.55), rgba(254,226,226,0.6)), url("{_data_url}") !important; }}
    </style>
    <div class="header-wrap">
      {_nav_html}
    </div>
    ''', unsafe_allow_html=True)
else:
    c1, c2 = st.columns([2, 2])
    with c2:
        if page != "landing":
            if st.button("Home", key="nav_home", use_container_width=True):
                st.session_state.page = "landing"
                st.rerun()
        if st.button("Submit an order", key="nav_order", use_container_width=True):
            st.session_state.page = "book"
            st.rerun()
        if st.button("Admin Portal", key="nav_admin", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

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
            lat, lon = float(parts[0].strip()), float(parts[1].strip())
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
                float(parts[0].strip()); float(parts[1].strip())
                return True
            except ValueError:
                pass
    return False


st.markdown("---")

# ---- Landing ----
def render_landing():
    hero = """
    <div class="brand-hero">
      <div class="logo">Load Logic <span class="est">Est. 1995</span></div>
      <div class="tagline">Affordable, dependable, quick heating oil delivery. Family-run, reliable delivery and exceptional customer service at competitive prices.</div>
    </div>
    """
    st.markdown(hero, unsafe_allow_html=True)
    img_path = os.path.join(os.path.dirname(__file__), "app", "static", "images", "load_logic_truck.png")
    if os.path.isfile(img_path):
        st.image(img_path, use_container_width=True, caption="Load Logic — here for you when you need us.")
    st.markdown("---")
    st.markdown("### Ready to order?")
    if st.button("**Submit an order**", type="primary", use_container_width=False):
        st.session_state.page = "book"
        st.rerun()


# ---- Book (Submit order) ----
def render_book():
    st.header("Submit an order")
    st.markdown("Request heating oil delivery. We’ll reach out to confirm.")
    with st.form("book_form"):
        name = st.text_input("Customer name *")
        email = st.text_input("Email *")
        phone = st.text_input("Phone *")
        address = st.text_area("Delivery address *", height=80)
        fuel = st.selectbox("Fuel type", ["Heating Oil", "Diesel", "Kerosene", "Other"], key="fuel")
        tank_loc = st.text_input("Tank location", placeholder="e.g. Basement")
        gallons = st.number_input("Order quantity (gallons)", 0.0, 5000.0, 275.0, 25.0)
        tank_empty = st.checkbox("Tank empty")
        priority = st.selectbox("Priority", ["Standard", "Rush", "Emergency"], key="priority")
        notes = st.text_area("Special considerations", placeholder="Optional", height=80)
        pay = st.selectbox("Payment", ["Credit Card", "Check", "Cash", "Other"], key="pay")
        submitted = st.form_submit_button("Submit booking")

    if submitted:
        if not all([name, email, phone, address]):
            st.error("Fill required fields: name, email, phone, address.")
            return
        geo = geocode_address_sync(address.strip())
        if not geo:
            st.error("Could not resolve address.")
            return
        lat, lon = geo
        if not _has_api_key():
            st.info("Using demo coordinates (no API key). Routes use synthetic data.")
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
            st.success(f"✅ Request **{req.id}** created. We’ll be in touch soon.")
        except Exception as e:
            st.error(str(e))


# ---- Route Planner ----
def render_route_planner():
    if st.button("← Dashboard", key="rp_back"):
        st.session_state.page = "dashboard"
        st.rerun()
    st.header("Route Planner")
    st.markdown("Plan optimized delivery routes with capacity constraints.")

    with st.expander("⚙️ Route settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            max_drivers = st.number_input("Max drivers", 1, 20, 6, key="rp_max_drivers")
        with c2:
            max_stops_per_driver = st.number_input("Max stops per driver", 1, 20, 7, key="rp_max_stops")
        with c3:
            truck_capacity = st.number_input("Truck capacity (gal)", 100, 10000, 2000, 100, key="rp_capacity")

    st.markdown("**Customer stops** — Add addresses below, or load from Requests.")
    load_pending = st.button("📋 Load pending requests as stops", key="rp_load_pending")
    load_selected = st.button("📋 Load selected requests as stops", key="rp_load_selected")
    if load_pending:
        pending = [r for r in requests_repo.list_requests(status="pending") if r.lat and r.lon]
        if pending:
            st.session_state.stops = [{"address": r.delivery_address, "gallons": int(r.order_quantity_gallons or 0)} for r in pending]
            st.success(f"Loaded {len(pending)} pending request(s) as stops.")
            st.rerun()
        else:
            st.warning("No pending requests with coordinates. Use **Submit an order** or **Requests** first.")
    if load_selected:
        all_reqs = {r.id: r for r in requests_repo.list_requests()}
        sel = [all_reqs[rid] for rid in st.session_state.selected_request_ids if rid in all_reqs and all_reqs[rid].lat and all_reqs[rid].lon]
        if sel:
            st.session_state.stops = [{"address": r.delivery_address, "gallons": int(r.order_quantity_gallons or 0)} for r in sel]
            st.success(f"Loaded {len(sel)} selected request(s) as stops.")
            st.rerun()
        else:
            st.warning("No selected requests with coordinates. Select some on **Requests**, then try again.")

    st.caption("Use **➕ Add stop** in the form below to add more, or enter addresses manually.")
    with st.form("route_planner_form", clear_on_submit=False):
        depot_input = st.text_area("Depot address or coordinates", value=DEFAULT_DEPOT, placeholder="123 Depot Rd or 40.7128,-74.0060", height=80)
        st.markdown("Stops:")
        for i, stop in enumerate(st.session_state.stops):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.session_state.stops[i]["address"] = st.text_input(f"Stop {i+1}", value=stop.get("address", ""), key=f"stop_a_{i}", placeholder="Address or lat,lon")
            with c2:
                st.session_state.stops[i]["gallons"] = st.number_input("Gal", 0, 10000, int(stop.get("gallons", 0)), key=f"stop_g_{i}")
        add_clicked = st.form_submit_button("➕ Add stop")
        submitted = st.form_submit_button("🚗 Plan routes")

    if add_clicked:
        st.session_state.stops.append({"address": "", "gallons": 0})
        st.rerun()
    if st.button("🗑️ Remove last stop", key="rp_remove_last") and len(st.session_state.stops) > 1:
        st.session_state.stops.pop()
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
                depot_coords = geocode_address_sync(depot_input.strip())
                if not depot_coords:
                    st.error("Could not resolve depot.")
                    return

            processed = []
            for i, s in enumerate(valid):
                addr = (s.get("address") or "").strip()
                g = float(s.get("gallons", 0) or 0)
                if is_coordinate_string(addr):
                    coords = parse_coordinates(addr)
                    if coords:
                        processed.append({"id": i + 1, "address": addr, "lat": coords[0], "lon": coords[1], "gallons": g})
                else:
                    geo = geocode_address_sync(addr)
                    if geo:
                        processed.append({"id": i + 1, "address": addr, "lat": geo[0], "lon": geo[1], "gallons": g})
                    else:
                        st.warning(f"Could not resolve: {addr}")

            if not processed:
                st.error("No valid stops.")
                return

            router = DeliveryRouter(depot_coords, num_trucks=max_drivers, max_stops_per_truck=max_stops_per_driver, truck_capacity=truck_capacity)
            plan = router.create_full_routing_plan(processed, use_google_optimization=_has_api_key())

            st.success(f"✅ {len([k for k in plan if k != 'summary'])} route(s)")
            if not _has_api_key():
                st.caption("Using demo coordinates and synthetic travel times.")
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
                coords = []
                total_g = 0
                for s in stops_list:
                    a = s.get("address") or (f"{s['lat']},{s['lon']}" if "lat" in s else "")
                    if a:
                        addrs.append(a)
                        coords.append((s["lat"], s["lon"]) if "lat" in s and "lon" in s else None)
                    total_g += float(s.get("gallons", 0))
                if not addrs:
                    continue
                use_coords = all(c is not None for c in coords) and len(coords) == len(addrs)
                stop_coords = coords if use_coords else None
                link = multi_stop_link(
                    depot_display, addrs,
                    depot_coords=depot_coords,
                    stop_coords=stop_coords,
                )
                with st.expander(f"🚛 {key.replace('_', ' ')} — {len(stops_list)} stops, {total_g:.0f} gal", expanded=True):
                    st.markdown(f"[🗺️ Google Maps]({link})")
                    for j, a in enumerate(addrs, 1):
                        st.markdown(f"{j}. {a}")


# ---- Requests ----
def render_requests():
    if st.button("← Dashboard", key="req_back"):
        st.session_state.page = "dashboard"
        st.rerun()
    st.header("Requests")
    st.markdown("Select the requests you want to route. Then go to **Dashboard** and use **Create routes from selected**.")

    status_filter = st.selectbox("Filter", ["all", "pending", "assigned", "completed", "cancelled"], key="req_filter")
    status = None if status_filter == "all" else status_filter
    requests_list = requests_repo.list_requests(status=status)

    if not requests_list:
        st.info("No requests. Customers can **Submit an order** from the home page.")
        return

    for r in requests_list:
        addr_short = (r.delivery_address[:50] + "…") if len(r.delivery_address) > 50 else r.delivery_address
        sel = st.checkbox(
            f"{addr_short} — `{r.status}`",
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

    n_sel = len(st.session_state.selected_request_ids)
    if n_sel > 0:
        st.markdown("---")
        if st.button(f"Route {n_sel} selected → Dashboard", type="primary", key="req_to_dash"):
            st.session_state.page = "dashboard"
            st.rerun()
        st.caption("Your selection is used in **Create routes from selected requests** on the Dashboard.")


# ---- Dashboard ----
def render_dashboard():
    st.header("Admin Dashboard")
    st.markdown("Manage delivery requests and plan routes.")

    if st.button("🗺️ **Route Planner**", type="primary", use_container_width=True):
        st.session_state.page = "route_planner"
        st.rerun()
    st.caption("Build optimized routes from depot and stops.")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📋 **Requests**", type="primary", use_container_width=True):
        st.session_state.page = "requests"
        st.rerun()
    st.caption("View and select delivery requests.")

    st.markdown("---")
    st.subheader("Create routes from selected requests")

    pending = [r for r in requests_repo.list_requests(status="pending") if r.lat and r.lon]
    drivers = drivers_repo.get_all_drivers()

    if not drivers:
        st.warning("No drivers in `data/drivers.json`. Add drivers first.")
        return
    if not pending:
        st.info("No pending requests with coordinates. Use **Submit an order** to add requests (demo coords when API unavailable).")
        return

    eligible_ids = {r.id for r in pending}
    selected = set(st.session_state.selected_request_ids) & eligible_ids
    if not selected:
        selected = eligible_ids

    st.markdown(f"**{len(selected)}** request(s) selected for routing.")
    depot = st.text_input("Depot address *", value=DEFAULT_DEPOT, placeholder="123 Depot Rd or 40.7128,-74.0060", key="dash_depot")
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

        dep_coords = geocode_address_sync(depot.strip())
        if not dep_coords:
            st.error("Could not resolve depot.")
            return
        depot_loc = dep_coords
        depot_str = depot.strip()
        if not _has_api_key():
            st.caption("Using demo coordinates and synthetic travel times.")

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
                        "id": r.id, "address": r.delivery_address, "lat": r.lat, "lon": r.lon,
                        "service_minutes": 20, "access_instructions": r.access_instructions, "gate_code": None,
                        "tank_location": r.tank_location, "customer_notes": r.special_considerations, "payment_required": False,
                    })
            addrs = [e["address"] for e in enriched]
            stop_coords = [(e["lat"], e["lon"]) for e in enriched]
            link = multi_stop_link(
                depot_str, addrs,
                depot_coords=(depot_loc[0], depot_loc[1]),
                stop_coords=stop_coords,
            )
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


# ---- Main content ----
if page == "landing":
    render_landing()
elif page == "book":
    render_book()
elif page == "dashboard":
    render_dashboard()
elif page == "route_planner":
    render_route_planner()
else:
    render_requests()

# ---- Footer ----
st.markdown("---")
st.caption("© 2025 Load Logic — All Rights Reserved. Affordable, dependable, quick heating oil delivery.")
