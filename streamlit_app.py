"""
Streamlit app for the Heating Oil Route Planner
Deployed to Streamlit Cloud
"""

import streamlit as st
import sys
import os
import asyncio
from typing import List, Dict, Any, Tuple, Optional

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import config to load environment variables
import app.config  # noqa: F401

from app.services.maps import geocode_address, has_google_key
from app.services.delivery_router import DeliveryRouter
from app.services.links import multi_stop_link

# Page configuration
st.set_page_config(
    page_title="Heating Oil Route Planner",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'stops' not in st.session_state:
    st.session_state.stops = [{"address": "", "gallons": 0}]

def parse_coordinates(coord_str: str) -> Optional[Tuple[float, float]]:
    """Parse coordinates from string like '40.7128,-74.0060' or '40.7128, -74.0060'"""
    try:
        parts = coord_str.strip().split(',')
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
    except (ValueError, AttributeError):
        pass
    return None

def is_coordinate_string(s: str) -> bool:
    """Check if string looks like coordinates"""
    s = s.strip()
    if ',' in s:
        parts = s.split(',')
        if len(parts) == 2:
            try:
                float(parts[0].strip())
                float(parts[1].strip())
                return True
            except ValueError:
                pass
    return False

def main():
    st.title("🛢️ Heating Oil Route Planner")
    st.markdown("Plan optimized delivery routes with capacity constraints")
    
    # Check Google Maps API status
    has_api_key = has_google_key()
    if has_api_key:
        st.success("✅ Google Maps API configured")
    else:
        st.warning("⚠️ Google Maps API not configured - using coordinates only. Set GOOGLE_MAPS_API_KEY in Streamlit secrets.")
    
    st.markdown("---")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        max_drivers = st.number_input("Max drivers", min_value=1, max_value=20, value=6, step=1)
        max_stops_per_driver = st.number_input("Max stops per driver", min_value=1, max_value=20, value=7, step=1)
        truck_capacity = st.number_input("Truck capacity (gallons)", min_value=100, max_value=10000, value=2000, step=100)
        
        st.markdown("---")
        st.markdown("### 📝 Instructions")
        st.markdown("""
        1. Enter depot address or coordinates (lat,lon)
        2. Add customer stops with addresses or coordinates
        3. Optionally specify gallons per stop
        4. Click "Plan Routes" to generate optimized routes
        """)
    
    # Main form
    with st.form("route_planner_form"):
        st.header("Route Planning")
        
        # Depot input
        depot_input = st.text_area(
            "Depot address or coordinates",
            placeholder="123 Depot Rd, City, State ZIP\nor: 40.7128,-74.0060",
            height=80,
            help="Enter an address or coordinates in format: lat,lon"
        )
        
        st.markdown("### Customer Stops")
        
        # Dynamic stops input
        stops_container = st.container()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("➕ Add Stop", type="secondary"):
                st.session_state.stops.append({"address": "", "gallons": 0})
                st.rerun()
        
        # Display stops
        stops_to_remove = []
        for i, stop in enumerate(st.session_state.stops):
            with stops_container:
                cols = st.columns([4, 1, 0.5])
                with cols[0]:
                    stop["address"] = st.text_input(
                        f"Stop {i+1} - Address or coordinates",
                        value=stop["address"],
                        key=f"stop_addr_{i}",
                        placeholder="123 Main St, City, State ZIP or 40.7128,-74.0060"
                    )
                with cols[1]:
                    stop["gallons"] = st.number_input(
                        "Gallons",
                        min_value=0,
                        value=int(stop.get("gallons", 0)),
                        key=f"stop_gallons_{i}",
                        step=1
                    )
                with cols[2]:
                    if st.button("🗑️", key=f"remove_{i}", help="Remove this stop"):
                        stops_to_remove.append(i)
        
        # Remove stops (after iteration to avoid index issues)
        for idx in reversed(stops_to_remove):
            st.session_state.stops.pop(idx)
        if stops_to_remove:
            st.rerun()
        
        # Submit button
        submitted = st.form_submit_button("🚗 Plan Routes", type="primary", use_container_width=True)
    
    # Process form submission
    if submitted:
        if not depot_input.strip():
            st.error("Please enter a depot address or coordinates")
            return
        
        # Filter out empty stops
        valid_stops = [s for s in st.session_state.stops if s.get("address", "").strip()]
        
        if not valid_stops:
            st.error("Please add at least one customer stop")
            return
        
        if len(valid_stops) > 50:
            st.error("Maximum 50 stops allowed")
            return
        
        with st.spinner("Planning routes... This may take a moment."):
            try:
                # Parse depot
                depot_coords = None
                depot_display = depot_input.strip()
                
                if is_coordinate_string(depot_input):
                    depot_coords = parse_coordinates(depot_input)
                    if not depot_coords:
                        st.error(f"Invalid depot coordinates: {depot_input}")
                        return
                else:
                    if has_api_key:
                        depot_coords = asyncio.run(geocode_address(depot_input.strip()))
                        if not depot_coords:
                            st.error(f"Could not geocode depot address: {depot_input}")
                            return
                    else:
                        st.error("Address geocoding requires Google Maps API key. Please use coordinates (lat,lon) format.")
                        return
                
                # Process stops
                processed_stops: List[Dict[str, Any]] = []
                for i, stop in enumerate(valid_stops):
                    addr = stop.get("address", "").strip()
                    gallons = float(stop.get("gallons", 0) or 0)
                    
                    if is_coordinate_string(addr):
                        coords = parse_coordinates(addr)
                        if coords:
                            processed_stops.append({
                                "id": i + 1,
                                "address": addr,
                                "lat": coords[0],
                                "lon": coords[1],
                                "gallons": gallons
                            })
                        else:
                            st.warning(f"Invalid coordinates for stop {i+1}: {addr}")
                    else:
                        if has_api_key:
                            geo = asyncio.run(geocode_address(addr))
                            if geo:
                                processed_stops.append({
                                    "id": i + 1,
                                    "address": addr,
                                    "lat": geo[0],
                                    "lon": geo[1],
                                    "gallons": gallons
                                })
                            else:
                                st.warning(f"Could not geocode stop {i+1}: {addr}")
                        else:
                            st.error(f"Address geocoding requires Google Maps API key. Use coordinates for stop {i+1}.")
                            return
                
                if not processed_stops:
                    st.error("No valid stops to process")
                    return
                
                # Create router and plan routes
                router = DeliveryRouter(
                    depot_coords,
                    num_trucks=max_drivers,
                    max_stops_per_truck=max_stops_per_driver,
                    truck_capacity=truck_capacity
                )
                
                plan = router.create_full_routing_plan(
                    processed_stops,
                    use_google_optimization=has_api_key
                )
                
                # Display results
                st.markdown("---")
                st.header("📊 Route Plan Results")
                
                drivers = []
                for key in sorted(plan.keys()):
                    if key == "summary":
                        continue
                    truck = plan.get(key)
                    if not isinstance(truck, dict):
                        continue
                    stops = truck.get("stops") or []
                    if not stops:
                        continue
                    
                    # Get addresses for Google Maps link
                    addrs = []
                    total_gallons = 0
                    for stop in stops:
                        addr = stop.get("address", "")
                        if not addr and "lat" in stop and "lon" in stop:
                            addr = f"{stop['lat']},{stop['lon']}"
                        if addr:
                            addrs.append(addr)
                        total_gallons += float(stop.get("gallons", 0))
                    
                    if not addrs:
                        continue
                    
                    # Create Google Maps link
                    link = multi_stop_link(depot_display, addrs)
                    
                    drivers.append({
                        "driver": key.replace("_", " ").title(),
                        "google_maps_link": link,
                        "ordered_deliveries": addrs,
                        "total_gallons": total_gallons,
                        "num_stops": len(stops),
                        "feasible": total_gallons <= truck_capacity
                    })
                
                # Summary
                st.success(f"✅ Generated {len(drivers)} driver route(s)")
                
                # Display each driver's route
                for i, driver in enumerate(drivers):
                    with st.expander(f"🚛 {driver['driver']} - {driver['num_stops']} stops, {driver['total_gallons']:.0f} gallons", expanded=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if driver['feasible']:
                                st.success(f"✅ Capacity: {driver['total_gallons']:.0f} / {truck_capacity} gallons")
                            else:
                                st.error(f"⚠️ Over capacity: {driver['total_gallons']:.0f} / {truck_capacity} gallons")
                        
                        with col2:
                            st.markdown(f"[🗺️ Open in Google Maps]({driver['google_maps_link']})")
                        
                        st.markdown("**Delivery Order:**")
                        for j, delivery in enumerate(driver['ordered_deliveries'], 1):
                            st.markdown(f"{j}. {delivery}")
                
            except Exception as e:
                st.error(f"Error planning routes: {str(e)}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
