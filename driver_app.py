"""
Driver Mobile Interface - Streamlit App

Run with: streamlit run driver_app.py
"""

import streamlit as st
from urllib.parse import urlencode

# Import mock data services
from app.services.mock_driver_data import (
    get_drivers,
    get_driver,
    get_route_for_driver,
    get_delivery_with_route_info,
    start_delivery,
    complete_delivery,
    get_route_progress,
)

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Load Logic - Driver",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# CUSTOM CSS FOR MOBILE
# ============================================================================

st.markdown("""
<style>
    /* Mobile-optimized styling */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1rem;
        font-size: 1.1rem;
        border-radius: 12px;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #4c8dff;
        color: white;
    }
    
    /* Card-like containers */
    .delivery-card {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    
    /* Status badges */
    .status-pending { color: #888; }
    .status-in-progress { color: #f0ad4e; }
    .status-completed { color: #5cb85c; }
    
    /* Payment required badge */
    .payment-required {
        background: #d9534f;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    
    /* Info boxes */
    .info-box {
        background: #1e3a5f;
        border-left: 4px solid #4c8dff;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        color: #ffffff;
        font-size: 1rem;
    }
    
    .info-box strong {
        color: #7cb3ff;
    }
    
    .warning-box {
        background: #4a3a1a;
        border-left: 4px solid #f0ad4e;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        color: #ffffff;
    }
    
    /* Gate code highlight */
    .gate-code {
        background: #2d5a2d;
        border: 3px solid #7ed67e;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        font-family: monospace;
        letter-spacing: 0.3rem;
        color: #ffffff;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    /* Hide Streamlit branding for cleaner mobile look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Larger touch targets */
    .row-widget.stRadio > div {
        gap: 0.5rem;
    }
    .row-widget.stRadio > div > label {
        padding: 0.75rem 1rem;
        border: 1px solid #333;
        border-radius: 8px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def maps_navigation_url(address: str) -> str:
    """Generate Google Maps navigation URL for an address."""
    params = {
        "api": "1",
        "destination": address,
        "travelmode": "driving",
    }
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def format_status(status: str) -> str:
    """Format status with emoji."""
    status_map = {
        "pending": "⏳ Pending",
        "in_progress": "🚚 In Progress",
        "completed": "✅ Completed",
    }
    return status_map.get(status, status)


def get_status_color(status: str) -> str:
    """Get color for status."""
    colors = {
        "pending": "gray",
        "in_progress": "orange",
        "completed": "green",
    }
    return colors.get(status, "gray")


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "screen" not in st.session_state:
    st.session_state.screen = "driver_select"

if "driver_id" not in st.session_state:
    st.session_state.driver_id = None

if "delivery_id" not in st.session_state:
    st.session_state.delivery_id = None


def navigate_to(screen: str, **kwargs):
    """Navigate to a different screen."""
    st.session_state.screen = screen
    for key, value in kwargs.items():
        st.session_state[key] = value


# ============================================================================
# SCREEN: DRIVER SELECTION
# ============================================================================

def show_driver_select():
    st.title("🚛 Load Logic")
    st.subheader("Driver Portal")
    st.write("Select your name to view today's route:")
    
    st.divider()
    
    drivers = get_drivers()
    
    for driver in drivers:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            has_route = driver.get("route_id") is not None
            route_status = "📋 Route assigned" if has_route else "No route today"
            
            if st.button(
                f"**{driver['name']}**\n\n{route_status}",
                key=f"driver-{driver['id']}",
                use_container_width=True,
                disabled=not has_route,
            ):
                navigate_to("manifest", driver_id=driver["id"])
                st.rerun()
        
        with col2:
            if driver.get("route_id"):
                progress = get_route_progress(driver["route_id"])
                st.metric(
                    label="Stops",
                    value=f"{progress['completed']}/{progress['total']}",
                )
        
        st.write("")  # Spacing


# ============================================================================
# SCREEN: ROUTE MANIFEST
# ============================================================================

def show_manifest():
    driver = get_driver(st.session_state.driver_id)
    route = get_route_for_driver(st.session_state.driver_id)
    
    if not route:
        st.error("No route found")
        if st.button("← Back"):
            navigate_to("driver_select")
            st.rerun()
        return
    
    # Header
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back"):
            navigate_to("driver_select")
            st.rerun()
    with col2:
        st.subheader(f"👋 {driver['name']}")
    
    # Route summary
    progress = get_route_progress(route["id"])
    
    st.markdown(f"### 📅 Route for {route['date']}")
    
    # Progress bar
    if progress["total"] > 0:
        completion_pct = progress["completed"] / progress["total"]
        st.progress(completion_pct, text=f"{progress['completed']} of {progress['total']} stops completed")
    
    st.divider()
    
    # Deliveries list
    for delivery in route["deliveries"]:
        status_color = get_status_color(delivery["status"])
        status_emoji = "✅" if delivery["status"] == "completed" else "🚚" if delivery["status"] == "in_progress" else "⏳"
        
        with st.container():
            # Delivery card
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Highlight current delivery
                if delivery["status"] == "in_progress":
                    st.markdown(f"### {status_emoji} Stop #{delivery['sequence']} - CURRENT")
                else:
                    st.markdown(f"**{status_emoji} Stop #{delivery['sequence']}**")
                
                st.write(f"📍 {delivery['address']}")
                st.caption(f"ETA: {delivery['eta']} • {delivery['customer_name']}")
                
                # Payment badge
                if delivery["payment_required"]:
                    st.markdown("💵 **Payment Required**")
            
            with col2:
                st.write("")  # Spacing for alignment
                if delivery["status"] == "completed":
                    st.success(f"{delivery['gallons_delivered']} gal")
            
            # View details button
            if st.button(
                "View Details →",
                key=f"view-{delivery['id']}",
                use_container_width=True,
            ):
                navigate_to("detail", delivery_id=delivery["id"])
                st.rerun()
            
            st.divider()
    
    # Summary footer
    if progress["completed"] == progress["total"] and progress["total"] > 0:
        st.success("🎉 All deliveries complete! Return to depot.")
        st.markdown(f"**Depot:** {route['depot']}")
        if st.link_button(
            "🗺️ Navigate to Depot",
            maps_navigation_url(route["depot"]),
            use_container_width=True,
        ):
            pass


# ============================================================================
# SCREEN: DELIVERY DETAIL
# ============================================================================

def show_delivery_detail():
    delivery = get_delivery_with_route_info(st.session_state.delivery_id)
    
    if not delivery:
        st.error("Delivery not found")
        if st.button("← Back"):
            navigate_to("manifest")
            st.rerun()
        return
    
    # Back button
    if st.button("← Back to Route"):
        navigate_to("manifest")
        st.rerun()
    
    # Header with customer name
    st.title(f"📍 Stop #{delivery['sequence']}")
    st.subheader(delivery["customer_name"])
    
    # Status
    st.markdown(f"**Status:** {format_status(delivery['status'])}")
    
    # Address and navigation
    st.markdown("---")
    st.markdown(f"### 🏠 Address")
    st.markdown(f"**{delivery['address']}**")
    st.caption(f"ETA: {delivery['eta']}")
    
    st.link_button(
        "🗺️ Open in Google Maps",
        maps_navigation_url(delivery["address"]),
        use_container_width=True,
        type="primary",
    )
    
    # Delivery Instructions Section
    st.markdown("---")
    st.markdown("### 📋 Delivery Instructions")
    
    # Gate code - prominently displayed if present
    if delivery.get("gate_code"):
        st.markdown("**🔐 Gate Code:**")
        st.markdown(f"""
        <div class="gate-code">{delivery['gate_code']}</div>
        """, unsafe_allow_html=True)
        st.write("")  # Spacing
    
    # Tank location
    if delivery.get("tank_location"):
        st.info(f"**🛢️ Tank Location:**\n\n{delivery['tank_location']}")
    
    # Access notes
    if delivery.get("access_notes"):
        st.warning(f"**⚠️ Access Notes:**\n\n{delivery['access_notes']}")
    
    # Customer Notes Section
    st.markdown("---")
    st.markdown("### 📝 Customer Notes")
    
    # Payment required - very prominent
    if delivery.get("payment_required"):
        st.error("💵 **PAYMENT REQUIRED** - Collect payment before leaving")
    else:
        st.success("✓ No payment required")
    
    # Account notes
    if delivery.get("account_notes"):
        st.markdown(f"""
        <div class="info-box">
            <strong>Account Notes:</strong><br>
            {delivery['account_notes']}
        </div>
        """, unsafe_allow_html=True)
    
    # Completion info if already completed
    if delivery["status"] == "completed":
        st.markdown("---")
        st.markdown("### ✅ Completion Details")
        st.success(f"**Gallons Delivered:** {delivery['gallons_delivered']}")
        if delivery.get("completion_notes"):
            st.write(f"**Notes:** {delivery['completion_notes']}")
        st.caption(f"Completed at: {delivery['completed_at']}")
    
    # Action buttons
    st.markdown("---")
    
    if delivery["status"] == "pending":
        if st.button("🚚 Start This Delivery", type="primary", use_container_width=True):
            start_delivery(delivery["id"])
            st.rerun()
    
    elif delivery["status"] == "in_progress":
        if st.button("✅ Mark Complete", type="primary", use_container_width=True):
            navigate_to("complete", delivery_id=delivery["id"])
            st.rerun()
    
    elif delivery["status"] == "completed":
        if delivery.get("next_delivery_id"):
            if st.button("➡️ Next Delivery", type="primary", use_container_width=True):
                navigate_to("detail", delivery_id=delivery["next_delivery_id"])
                st.rerun()
        else:
            st.info("This was the last delivery on your route!")


# ============================================================================
# SCREEN: COMPLETION FORM
# ============================================================================

def show_completion_form():
    delivery = get_delivery_with_route_info(st.session_state.delivery_id)
    
    if not delivery:
        st.error("Delivery not found")
        if st.button("← Back"):
            navigate_to("manifest")
            st.rerun()
        return
    
    st.title("✅ Complete Delivery")
    
    st.markdown(f"**{delivery['customer_name']}**")
    st.caption(delivery["address"])
    
    st.divider()
    
    # Gallons input
    gallons = st.number_input(
        "Gallons Delivered",
        min_value=0.0,
        max_value=1000.0,
        value=0.0,
        step=0.5,
        format="%.1f",
        help="Enter the number of gallons delivered",
    )
    
    # Notes input
    notes = st.text_area(
        "Delivery Notes (optional)",
        placeholder="Any notes about this delivery...",
        height=100,
    )
    
    # Payment reminder if required
    if delivery.get("payment_required"):
        st.warning("💵 **Reminder:** Payment was required for this delivery. Make sure you've collected it!")
        payment_collected = st.checkbox("Payment collected")
    else:
        payment_collected = True  # Not required
    
    st.divider()
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Cancel", use_container_width=True):
            navigate_to("detail", delivery_id=delivery["id"])
            st.rerun()
    
    with col2:
        confirm_disabled = gallons <= 0 or (delivery.get("payment_required") and not payment_collected)
        
        if st.button(
            "Confirm ✓",
            type="primary",
            use_container_width=True,
            disabled=confirm_disabled,
        ):
            # Complete the delivery
            complete_delivery(
                delivery["id"],
                gallons_delivered=gallons,
                notes=notes if notes else None,
            )
            
            st.success("Delivery completed!")
            
            # Navigate to next delivery or back to manifest
            if delivery.get("next_delivery_id"):
                navigate_to("detail", delivery_id=delivery["next_delivery_id"])
            else:
                navigate_to("manifest")
            st.rerun()
    
    if confirm_disabled:
        if gallons <= 0:
            st.caption("⚠️ Enter gallons delivered to continue")
        elif delivery.get("payment_required") and not payment_collected:
            st.caption("⚠️ Confirm payment was collected to continue")


# ============================================================================
# MAIN ROUTER
# ============================================================================

def main():
    # Route to appropriate screen
    screen = st.session_state.screen
    
    if screen == "driver_select":
        show_driver_select()
    elif screen == "manifest":
        show_manifest()
    elif screen == "detail":
        show_delivery_detail()
    elif screen == "complete":
        show_completion_form()
    else:
        # Fallback
        st.session_state.screen = "driver_select"
        st.rerun()


if __name__ == "__main__":
    main()
