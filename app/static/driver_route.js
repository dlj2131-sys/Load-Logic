/**
 * Driver Route Page
 * Displays a single driver's route with stops and navigation
 */

function $(id) {
  return document.getElementById(id);
}

async function loadRoute() {
  const routeId = getRouteId();
  if (!routeId) {
    showError("Invalid or missing route ID");
    return;
  }

  $("route-id").textContent = routeId;
  $("loading").style.display = "block";

  try {
    const response = await fetch(`/api/driver-route/${routeId}`);
    const data = await response.json();

    if (!response.ok || !data.route) {
      showError(data.error || "Route not found");
      return;
    }

    displayRoute(data.route, routeId);
  } catch (err) {
    showError(`Error loading route: ${err.message}`);
  }
}

function getRouteId() {
  const path = window.location.pathname;
  const match = path.match(/\/driver\/route\/([^/]+)/);
  return match ? match[1] : null;
}

function showError(message) {
  $("error").textContent = message;
  $("error").style.display = "block";
  $("loading").style.display = "none";
  $("route-section").style.display = "none";
}

function displayRoute(route, routeId) {
  $("loading").style.display = "none";
  $("route-section").style.display = "block";

  // Store route data for later use
  window.currentRoute = route;
  window.currentRouteId = routeId;

  // Driver info
  const driverName = route.driver_id || "Driver";
  const vehicleInfo = `Vehicle: ${driverName}`;

  $("driver-name").textContent = driverName;
  $("vehicle-info").textContent = vehicleInfo;
  $("route-id").textContent = routeId;

  // Summary
  const totalStops = route.stops.length;
  const completedStops = 0; // TODO: fetch completion status
  const remainingStops = totalStops - completedStops;

  $("total-stops").textContent = totalStops;
  $("completed-stops").textContent = completedStops;
  $("remaining-stops").textContent = remainingStops;

  // Progress
  const progressPercent = totalStops > 0 ? Math.round((completedStops / totalStops) * 100) : 0;
  $("progress-fill").style.width = progressPercent + "%";
  $("progress-text").textContent = `${progressPercent}% Complete`;

  // Google Maps link
  if (route.google_maps_link) {
    $("google-maps-btn").href = route.google_maps_link;
  }

  // Render stops as accordion
  renderStops(route.stops, route.ordered_deliveries);

  // Update progress
  updateProgress();
}

function updateProgress() {
  const route = window.currentRoute;
  if (!route) return;

  const totalStops = route.stops.length;
  const completedStops = totalStops - route.ordered_deliveries.length;
  const remainingStops = route.ordered_deliveries.length;

  $("completed-stops").textContent = completedStops;
  $("remaining-stops").textContent = remainingStops;

  const progressPercent = totalStops > 0 ? Math.round((completedStops / totalStops) * 100) : 0;
  $("progress-fill").style.width = progressPercent + "%";
  $("progress-text").textContent = `${progressPercent}% Complete`;
}

function renderStops(stops, orderedDeliveryIds) {
  const container = $("stops-container");
  container.innerHTML = "";

  if (!orderedDeliveryIds || orderedDeliveryIds.length === 0) {
    container.innerHTML = "<p>No stops assigned</p>";
    return;
  }

  orderedDeliveryIds.forEach((stopId, index) => {
    const stop = stops.find(s => s.id === stopId);
    if (!stop) return;

    const isFirst = index === 0;
    const accordionItem = document.createElement("div");
    accordionItem.className = `accordion-item ${isFirst ? "active" : ""}`;
    accordionItem.id = `accordion-${escapeAttr(stop.id)}`;

    accordionItem.innerHTML = `
      <div class="accordion-header" onclick="toggleAccordion('${escapeAttr(stop.id)}')">
        <div class="accordion-header-left">
          <div class="stop-number-badge">${index + 1}</div>
          <div class="accordion-header-text">
            <h4>${escapeHtml(stop.address)}</h4>
            <p>${stop.service_minutes || 20} min service</p>
          </div>
        </div>
        <div class="accordion-toggle">▼</div>
      </div>
      <div class="accordion-content">
        <div class="accordion-body">
          <div class="delivery-details">
            <!-- Location & Navigation -->
            <div class="detail-group">
              <div class="detail-label">📍 Location</div>
              <div class="detail-value">${escapeHtml(stop.address)}</div>
              <a href="https://www.google.com/maps/search/${encodeURIComponent(stop.address)}" target="_blank" rel="noreferrer" class="btn btn-secondary" style="margin-top: 8px; display: inline-block;">
                📍 Navigate to Location
              </a>
            </div>

            ${
              stop.tank_location
                ? `<div class="detail-group">
                    <div class="detail-label">⛽ Tank Location</div>
                    <div class="detail-value">${escapeHtml(stop.tank_location)}</div>
                  </div>`
                : ""
            }

            ${
              stop.gate_code
                ? `<div class="detail-group">
                    <div class="detail-label">🔐 Gate Code</div>
                    <div class="detail-value gate-code-box">${escapeHtml(stop.gate_code)}</div>
                  </div>`
                : ""
            }

            ${
              stop.customer_notes
                ? `<div class="detail-group">
                    <div class="detail-label">📝 Special Instructions</div>
                    <div class="detail-value">${escapeHtml(stop.customer_notes)}</div>
                  </div>`
                : ""
            }

            ${
              stop.payment_required
                ? `<div class="detail-group">
                    <div class="detail-label">💰 Payment</div>
                    <div class="detail-value payment-indicator required">💰 Payment Required</div>
                  </div>`
                : `<div class="detail-group">
                    <div class="detail-label">💰 Payment</div>
                    <div class="detail-value payment-indicator not-required">✓ No payment required</div>
                  </div>`
            }

            <!-- Completion Form -->
            <div class="completion-form">
              <h4>Complete Delivery</h4>
              <div class="form-group">
                <label for="gallons-${escapeAttr(stop.id)}">Gallons Delivered:</label>
                <input type="number" id="gallons-${escapeAttr(stop.id)}" placeholder="0" min="0" step="0.1">
              </div>
              <div class="form-group">
                <label for="notes-${escapeAttr(stop.id)}">Delivery Notes (optional):</label>
                <textarea id="notes-${escapeAttr(stop.id)}" placeholder="Any issues or notes..." style="min-height: 60px;"></textarea>
              </div>
              <button class="btn-complete-delivery" onclick="completeDelivery('${escapeAttr(stop.id)}')">✓ Complete Delivery</button>
            </div>
          </div>
        </div>
      </div>
    `;
    container.appendChild(accordionItem);
  });
}

function toggleAccordion(stopId) {
  const accordionItem = document.getElementById(`accordion-${escapeAttr(stopId)}`);
  if (!accordionItem) return;

  accordionItem.classList.toggle("active");
}

function closeAccordion(stopId) {
  const accordionItem = document.getElementById(`accordion-${escapeAttr(stopId)}`);
  if (accordionItem) {
    accordionItem.classList.remove("active");
  }
}

function openAccordion(stopId) {
  const accordionItem = document.getElementById(`accordion-${escapeAttr(stopId)}`);
  if (accordionItem) {
    accordionItem.classList.add("active");
    // Scroll into view
    setTimeout(() => {
      accordionItem.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }
}

async function completeDelivery(stopId) {
  const gallons = parseFloat(document.getElementById(`gallons-${escapeAttr(stopId)}`).value) || 0;
  const notes = document.getElementById(`notes-${escapeAttr(stopId)}`).value.trim();
  const route = window.currentRoute;

  if (!route) {
    showInAppMessage("No route data available", "error");
    return;
  }

  const currentStop = route.stops.find(s => s.id === stopId);
  if (!currentStop) {
    showInAppMessage("Stop not found", "error");
    return;
  }

  // Show success message
  showInAppMessage(`✓ Delivery Complete!\n\nGallons: ${gallons}\nNotes: ${notes || "(none)"}`, "success");

  // Close current accordion
  closeAccordion(stopId);

  // Remove completed stop and advance to next
  const currentIndex = route.ordered_deliveries.indexOf(stopId);
  if (currentIndex > -1) {
    route.ordered_deliveries.splice(currentIndex, 1);
  }

  // Open next delivery
  if (route.ordered_deliveries.length > 0) {
    setTimeout(() => {
      openAccordion(route.ordered_deliveries[0]);
    }, 500);
  } else {
    // All deliveries complete
    setTimeout(() => {
      showInAppMessage("🎉 All deliveries complete!", "success");
    }, 500);
  }

  // Update progress
  updateProgress();
}

function showInAppMessage(message, type = "info") {
  // Create modal overlay
  const overlay = document.createElement("div");
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  `;

  // Create modal box
  const modal = document.createElement("div");
  modal.style.cssText = `
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 32px;
    max-width: 90%;
    width: 400px;
    text-align: center;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  `;

  // Determine message styling
  let bgColor = "#334155";
  let textColor = "#f1f5f9";
  let icon = "ℹ️";

  if (type === "success") {
    bgColor = "rgba(16, 185, 129, 0.15)";
    textColor = "#86efac";
    icon = "✓";
  } else if (type === "error") {
    bgColor = "rgba(239, 68, 68, 0.15)";
    textColor = "#fca5a5";
    icon = "✕";
  }

  modal.innerHTML = `
    <div style="font-size: 48px; margin-bottom: 16px;">${icon}</div>
    <p style="color: ${textColor}; font-size: 16px; line-height: 1.6; white-space: pre-wrap; word-break: break-word;">${escapeHtml(message)}</p>
  `;

  modal.style.background = bgColor;
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // Close on click
  overlay.addEventListener("click", () => {
    overlay.remove();
  });

  modal.addEventListener("click", (e) => {
    e.stopPropagation();
  });

  // Auto-close after 3 seconds
  setTimeout(() => {
    if (overlay.parentNode) {
      overlay.remove();
    }
  }, 3000);
}

function advanceToNextDelivery() {
  const route = window.currentRoute;
  if (!route || !route.ordered_deliveries || route.ordered_deliveries.length <= 1) {
    return;
  }

  // Remove current stop and show next
  route.ordered_deliveries.shift();
  displayCurrentDelivery(route.stops, route.ordered_deliveries[0]);

  // Re-render stops list
  renderStops(route.stops, route.ordered_deliveries);

  // Scroll to next delivery
  const section = $("current-delivery-section");
  if (section) {
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function escapeHtml(str) {
  return (str || "").replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[m]));
}

function escapeAttr(str) {
  return (str || "").replace(/'/g, "&#39;").replace(/"/g, "&quot;");
}

// Load on page load
window.addEventListener("DOMContentLoaded", () => {
  loadRoute();
});
