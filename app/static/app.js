function $(id) { return document.getElementById(id); }

/**
 * Parse a single input line as either address or lat,lon coordinates.
 * Returns { type: 'address' | 'coords', value: string | {lat, lon} } or null if invalid
 */
function parseAddressOrCoords(text) {
  const trimmed = (text || "").trim();
  if (!trimmed) return null;

  // Try to match lat,lon format
  const coordMatch = trimmed.match(/^([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)$/);
  if (coordMatch) {
    const lat = parseFloat(coordMatch[1]);
    const lon = parseFloat(coordMatch[2]);

    // Validate lat/lon ranges
    if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      return { type: 'coords', value: { lat, lon } };
    }
  }

  // Otherwise treat as address
  return { type: 'address', value: trimmed };
}

function setStatus(msg) {
  const el = $("status");
  if (el) el.textContent = msg || "";
}

function escapeHtml(str) {
  return (str ?? "").replace(/[&<>"']/g, (m) => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[m]));
}

function driverCard(driver, index, allDrivers) {
  const ok = !!driver.feasible;
  const badge = ok ? `<span class="badge ok">Feasible</span>` : `<span class="badge warn">Not feasible</span>`;
  const link = driver.google_maps_link
    ? `<a class="btn primary" href="${driver.google_maps_link}" target="_blank" rel="noreferrer">📍 Open in Google Maps</a>`
    : "";
  const driverPageLink = driver.route_id
    ? `<a class="btn secondary" href="/driver/route/${driver.route_id}" target="_blank" rel="noreferrer">👤 Driver Page</a>`
    : "";
  const err = driver.error ? `<div class="error" style="margin-top:8px;">${escapeHtml(driver.error)}</div>` : "";

  return `
    <section class="card" style="margin-top:12px;">
      <div class="row-between">
        <h3 style="margin:0;">${escapeHtml(driver.driver_name || driver.driver || "Driver")}</h3>
        <div>${badge}</div>
      </div>
      <div class="row wrap" style="margin-top:8px;">
        <div>${link}</div>
        <div>${driverPageLink}</div>
      </div>
      ${err}
      <details style="margin-top:8px;">
        <summary>Stops (${(driver.ordered_deliveries || []).length})</summary>
        <ol>${(driver.ordered_deliveries || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>
      </details>
    </section>
  `;
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const txt = await r.text();
  let json = null;
  try { json = JSON.parse(txt); } catch (e) { /* ignore */ }
  return { status: r.status, json, text: txt };
}

function fillDemo() {
  $("depot").value = "40.9176,-74.2591";
  $("stops_bulk").value = [
    "40.9280,-74.2450",
    "40.9100,-74.2700",
    "40.9050,-74.2600",
    "40.9200,-74.2500",
    "40.9150,-74.2400",
    "40.7580,-73.9855",
    "40.7489,-73.9680",
  ].join("\n");
}

function escapeAttr(str) {
  return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

async function sendRoutesToDrivers(planJson) {
  const sendBtn = document.querySelector("#send-routes-btn");
  if (!sendBtn) return;

  sendBtn.disabled = true;
  sendBtn.textContent = "📤 Sending routes...";

  try {
    // Get the current depot and plan
    const depot = window.currentDepot;
    const plan = window.currentPlan;

    if (!depot || !plan) {
      throw new Error("No plan data available");
    }

    // Parse depot coordinates
    let depotCoords;
    if (depot.type === "coords") {
      depotCoords = depot.value;
    } else {
      // If address, try to geocode first - for now use default
      $("error").style.display = "block";
      $("error").textContent = "Please use coordinates (lat,lon) for depot for now.";
      sendBtn.disabled = false;
      sendBtn.textContent = "📤 Send Routes to Drivers";
      return;
    }

    // Prepare request body with stops from the plan
    const stops_input = $("stops_bulk").value.trim();
    const stopLines = stops_input.split(/\r?\n/).map(s => s.trim()).filter(s => s.length > 0);
    const stops = [];

    for (const line of stopLines) {
      const parsed = parseAddressOrCoords(line);
      if (parsed) {
        if (parsed.type === "coords") {
          stops.push({ lat: parsed.value.lat, lon: parsed.value.lon, address: `${parsed.value.lat},${parsed.value.lon}` });
        } else {
          stops.push({ address: parsed.value });
        }
      }
    }

    const res = await postJSON("/api/routes/create", {
      depot: depotCoords,
      stops: stops,
      max_drivers: parseInt($("max_drivers").value, 10) || 6,
      max_stops_per_driver: parseInt($("max_stops_per_driver").value, 10) || 7,
    });

    sendBtn.disabled = false;

    if (!res.json || !res.json.success) {
      throw new Error(res.json?.error || "Failed to send routes");
    }

    // Show success message
    const smsInfo = res.json.sms_sent || [];
    let successMsg = `✅ Routes sent to ${smsInfo.length} driver(s)!\n\n`;
    smsInfo.forEach(sms => {
      successMsg += `• ${sms.driver_id}: ${sms.phone} (${sms.status})\n`;
    });

    $("error").style.display = "block";
    $("error").className = "success";
    $("error").textContent = successMsg;
    sendBtn.textContent = "✓ Routes Sent!";
    sendBtn.style.background = "#4caf50";

    // Update driver cards with route_id information from the response
    const routes = res.json.routes || [];
    const updatedDrivers = routes.map(route => ({
      driver_name: route.driver_name,
      driver_id: route.driver_id,
      route_id: route.route_id,
      ordered_deliveries: route.ordered_deliveries,
      google_maps_link: route.google_maps_link,
      num_stops: route.num_stops,
      feasible: true,
    }));

    // Re-render the driver cards with route links
    $("drivers").innerHTML = updatedDrivers.map(driverCard).join("");

  } catch (err) {
    sendBtn.disabled = false;
    sendBtn.textContent = "📤 Send Routes to Drivers";
    $("results").style.display = "block";
    $("error").style.display = "block";
    $("error").className = "error";
    $("error").textContent = `Error sending routes: ${err?.message || String(err)}`;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  $("fill-demo").addEventListener("click", fillDemo);

  $("plan-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    $("results").style.display = "none";
    $("error").style.display = "none";
    $("drivers").innerHTML = "";
    $("summary").innerHTML = "";

    const depot_input = $("depot").value.trim();
    const stops_input = $("stops_bulk").value.trim();
    const max_drivers = parseInt($("max_drivers").value, 10) || 6;
    const max_stops_per_driver = parseInt($("max_stops_per_driver").value, 10) || 7;

    if (!depot_input || !stops_input) {
      $("error").style.display = "block";
      $("error").textContent = "Please provide depot address and stops.";
      return;
    }

    // Parse depot
    const depotParsed = parseAddressOrCoords(depot_input);
    if (!depotParsed) {
      $("error").style.display = "block";
      $("error").textContent = "Invalid depot address/coordinates.";
      return;
    }

    // Parse stops
    const stopLines = stops_input.split(/\r?\n/).map(s => s.trim()).filter(s => s.length > 0);
    const stops = [];
    for (const line of stopLines) {
      const parsed = parseAddressOrCoords(line);
      if (!parsed) {
        $("error").style.display = "block";
        $("error").textContent = `Invalid stop: ${escapeHtml(line)}`;
        return;
      }
      stops.push(parsed);
    }

    if (stops.length === 0) {
      $("error").style.display = "block";
      $("error").textContent = "Please provide at least one stop.";
      return;
    }

    setStatus("Planning routes...");
    $("plan-btn").disabled = true;

    try {
      const res = await postJSON("/api/plan-and-cluster", {
        depot: depotParsed,
        stops: stops,
        max_drivers,
        max_stops_per_driver,
      });

      $("plan-btn").disabled = false;
      setStatus("");

      if (!res.json) {
        throw new Error(res.text ? res.text.slice(0, 300) : "Request failed");
      }

      const data = res.json;
      if (!data.feasible) {
        $("results").style.display = "block";
        $("error").style.display = "block";
        $("error").textContent = data.error || "Clustering failed.";
        return;
      }

      const drivers = data.drivers || data.routes || [];
      const totalStops = drivers.reduce((n, d) => n + (d.ordered_deliveries || []).length, 0);

      $("summary").innerHTML = `
        <div class="row wrap">
          <div><div class="small">Drivers</div><div class="mono">${drivers.length}</div></div>
          <div><div class="small">Total stops</div><div class="mono">${totalStops}</div></div>
        </div>
        <div style="margin-top: 16px;">
          <button type="button" class="btn primary" id="send-routes-btn" onclick="sendRoutesToDrivers('${escapeAttr(JSON.stringify(data))}')">
            📤 Send Routes to Drivers
          </button>
        </div>
      `;

      $("drivers").innerHTML = drivers.map(driverCard).join("");
      $("results").style.display = "block";
      $("results").scrollIntoView({ behavior: "smooth", block: "start" });

      // Store the current plan for sending
      window.currentPlan = data;
      window.currentDepot = depotParsed;
    } catch (err) {
      $("plan-btn").disabled = false;
      setStatus("");
      $("results").style.display = "block";
      $("error").style.display = "block";
      $("error").textContent = err?.message || String(err);
    }
  });
});
