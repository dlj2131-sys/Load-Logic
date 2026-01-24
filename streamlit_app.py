"""
Streamlit frontend for Load Logic - Route Planning Application
Wraps the existing FastAPI backend
"""

import streamlit as st
import requests
import pandas as pd
from typing import Dict, List, Any, Optional
import os

# Configure page
st.set_page_config(
    page_title="Load Logic - Route Planner",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@st.cache_resource
def check_api_health() -> bool:
    """Check if API is available"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def parse_address_or_coords(text: str) -> Optional[Dict[str, Any]]:
    """Parse input as either address or coordinates (lat,lon)"""
    text = text.strip()
    if not text:
        return None

    parts = text.split(",")
    if len(parts) == 2:
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return {"type": "coords", "value": {"lat": lat, "lon": lon}}
        except ValueError:
            pass

    return {"type": "address", "value": text}


def plan_routes(depot: Dict, stops: List[Dict], max_drivers: int, max_stops_per_driver: int, truck_capacity: float):
    """Call the plan-and-cluster API endpoint"""
    payload = {
        "depot": depot,
        "stops": stops,
        "max_drivers": max_drivers,
        "max_stops_per_driver": max_stops_per_driver,
        "truck_capacity": truck_capacity,
    }

    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/plan-and-cluster",
            json=payload,
            timeout=30
        )
        return resp.json()
    except Exception as e:
        return {"feasible": False, "error": str(e)}


def list_delivery_requests():
    """Fetch pending delivery requests"""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/requests?status=pending",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("requests", [])
    except:
        pass
    return []


def create_delivery_request(customer_data: Dict) -> Optional[str]:
    """Create a new delivery request"""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/booking",
            json=customer_data,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("request_id")
    except:
        pass
    return None


def route_planner_page():
    """Route planning interface"""
    st.title("🗺️ Route Planner")

    col1, col2 = st.columns([2, 1])

    with col1:
        depot_input = st.text_input(
            "Depot address or coordinates",
            value="40.7589,-73.9851",
            help="Enter an address or lat,lon coordinates"
        )

    with col2:
        st.subheader("Settings")
        max_drivers = st.number_input("Max drivers", min_value=1, max_value=20, value=6)
        max_stops = st.number_input("Max stops/driver", min_value=1, max_value=20, value=7)
        truck_capacity = st.number_input("Truck capacity (gal)", min_value=100, max_value=5000, value=2000, step=100)

    st.divider()

    if "stops_data" not in st.session_state:
        st.session_state.stops_data = [{"address": "", "gallons": ""}]

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ Add Stop"):
            st.session_state.stops_data.append({"address": "", "gallons": ""})
            st.rerun()
    with col2:
        if st.button("📥 Demo Data"):
            st.session_state.stops_data = [
                {"address": "40.6372,-73.9760", "gallons": "300"},
                {"address": "40.7282,-73.7949", "gallons": "250"},
                {"address": "40.7180,-73.9854", "gallons": "400"},
                {"address": "40.8308,-73.9262", "gallons": "275"},
                {"address": "40.6486,-74.0756", "gallons": "225"},
            ]
            st.rerun()

    stops_df = pd.DataFrame(st.session_state.stops_data)
    edited_df = st.data_editor(
        stops_df,
        column_config={
            "address": st.column_config.TextColumn("Address/Coords", width="large"),
            "gallons": st.column_config.NumberColumn("Gallons", min_value=0, step=10),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    st.session_state.stops_data = edited_df.to_dict('records')

    if st.button("🚀 Plan Routes", type="primary", use_container_width=True):
        if not depot_input.strip():
            st.error("❌ Please enter depot")
            return

        valid_stops = [s for s in st.session_state.stops_data if s.get("address", "").strip()]
        if not valid_stops:
            st.error("❌ Please add stops")
            return

        depot_parsed = parse_address_or_coords(depot_input)
        if not depot_parsed:
            st.error("❌ Invalid depot")
            return

        stops_parsed = []
        for i, stop in enumerate(valid_stops):
            addr = stop.get("address", "").strip()
            parsed = parse_address_or_coords(addr)
            if not parsed:
                st.error(f"❌ Invalid stop {i + 1}")
                return

            gallons_val = stop.get("gallons", "")
            parsed["gallons"] = float(gallons_val) if gallons_val else 0
            stops_parsed.append(parsed)

        with st.spinner("🔄 Planning..."):
            result = plan_routes(
                depot=depot_parsed,
                stops=stops_parsed,
                max_drivers=max_drivers,
                max_stops_per_driver=max_stops,
                truck_capacity=truck_capacity
            )

        if result.get("feasible"):
            st.success("✅ Routes planned!")
            drivers = result.get("drivers", [])

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Drivers", len(drivers))
            with col2:
                total_stops = sum(len(d.get("ordered_deliveries", [])) for d in drivers)
                st.metric("Stops", total_stops)
            with col3:
                total_gal = sum(d.get("total_gallons", 0) for d in drivers)
                st.metric("Total Gal", f"{total_gal:.0f}")

            st.divider()

            for i, driver in enumerate(drivers, 1):
                with st.container(border=True):
                    st.markdown(f"### Driver {i}")
                    deliveries = driver.get("ordered_deliveries", [])
                    for j, delivery in enumerate(deliveries, 1):
                        if isinstance(delivery, dict):
                            addr = delivery.get("address", str(delivery))
                            gal = delivery.get("gallons", 0)
                            gal_str = f" ({gal} gal)" if gal > 0 else ""
                            st.text(f"{j}. {addr}{gal_str}")
                        else:
                            st.text(f"{j}. {delivery}")

                    if driver.get("google_maps_link"):
                        st.link_button("📍 Maps", driver["google_maps_link"])
        else:
            st.error(f"❌ {result.get('error', 'Unknown error')}")


def pending_requests_page():
    """Display pending requests"""
    st.title("📋 Pending Delivery Requests")

    with st.spinner("Loading..."):
        requests_list = list_delivery_requests()

    if not requests_list:
        st.info("No pending requests")
        return

    df_data = []
    for req in requests_list:
        df_data.append({
            "Customer": req.get("customer_name", ""),
            "Phone": req.get("customer_phone", ""),
            "Address": req.get("delivery_address", "")[:40],
            "Gallons": req.get("order_quantity_gallons", 0),
            "Priority": req.get("delivery_priority", ""),
        })

    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


def booking_page():
    """Booking form"""
    st.title("📦 Book Delivery")

    with st.form("booking_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *")
            email = st.text_input("Email *")
            phone = st.text_input("Phone *")

        with col2:
            address = st.text_input("Address *")
            requested_date = st.date_input("Delivery Date")
            priority = st.selectbox("Priority", ["Standard", "High", "Urgent"])

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            fuel = st.selectbox("Fuel Type", ["Heating Oil", "Diesel", "Other"])
            unit = st.selectbox("Unit", ["Furnace", "Boiler", "Other"])
            tank_loc = st.text_input("Tank Location")

        with col2:
            level = st.selectbox("Tank Level", ["5%", "10%", "15%", "20%", "25%", "30%", ">30%"])
            quantity = st.number_input("Quantity (gal) *", min_value=100, max_value=1000, value=275, step=25)
            empty = st.checkbox("Tank empty")

        access = st.text_area("Access Instructions")
        notes = st.text_area("Special Notes")
        payment = st.selectbox("Payment", ["Credit Card", "Check", "ACH", "Other"])

        if st.form_submit_button("📤 Submit", type="primary", use_container_width=True):
            if not all([name, email, phone, address]):
                st.error("Fill required fields")
            else:
                booking_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "address": address,
                    "fuelType": fuel,
                    "heatingUnit": unit,
                    "tankLocation": tank_loc,
                    "tankLevel": level,
                    "orderQuantity": quantity,
                    "tankEmpty": empty,
                    "deliveryDate": requested_date.isoformat(),
                    "deliveryPriority": priority,
                    "specialConsiderations": notes,
                    "paymentMethod": payment,
                    "accessInstructions": access,
                }

                with st.spinner("Submitting..."):
                    request_id = create_delivery_request(booking_data)

                if request_id:
                    st.success(f"✅ Booked! ID: {request_id}")
                else:
                    st.error("❌ Booking failed")


def dashboard_page():
    """Dashboard"""
    st.title("📊 Dashboard")

    all_requests = list_delivery_requests()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Requests", len(all_requests))
    with col2:
        urgent = len([r for r in all_requests if r.get("delivery_priority") == "Urgent"])
        st.metric("Urgent", urgent)
    with col3:
        total_gal = sum(r.get("order_quantity_gallons", 0) for r in all_requests)
        st.metric("Total Gal", f"{total_gal:.0f}")
    with col4:
        empty = len([r for r in all_requests if r.get("tank_empty")])
        st.metric("Empty Tanks", empty)

    st.divider()

    if all_requests:
        col1, col2 = st.columns(2)

        with col1:
            priority_counts = {}
            for r in all_requests:
                p = r.get("delivery_priority", "Standard")
                priority_counts[p] = priority_counts.get(p, 0) + 1
            st.subheader("By Priority")
            st.bar_chart(priority_counts)

        with col2:
            level_counts = {}
            for r in all_requests:
                l = r.get("current_tank_level", "Other")
                level_counts[l] = level_counts.get(l, 0) + 1
            st.subheader("Tank Levels")
            st.bar_chart(level_counts)


def main():
    with st.sidebar:
        st.markdown("# 🚚 Load Logic")
        st.markdown("Route Planning System")
        st.divider()

        page = st.radio(
            "Navigation",
            ["🗺️ Route Planner", "📋 Requests", "📦 Book", "📊 Dashboard"],
            label_visibility="collapsed"
        )

    api_healthy = check_api_health()
    if not api_healthy:
        st.error(f"⚠️ API unavailable at {API_BASE_URL}")
        st.info("Start backend: `python -m uvicorn app.main:app --reload`")
        return

    if page == "🗺️ Route Planner":
        route_planner_page()
    elif page == "📋 Requests":
        pending_requests_page()
    elif page == "📦 Book":
        booking_page()
    else:
        dashboard_page()


if __name__ == "__main__":
    main()
