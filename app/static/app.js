function $(id) { return document.getElementById(id); }

/**
 * Parse a single input line as either address or lat,lon coordinates, optionally with gallons.
 * Returns { type: 'address' | 'coords', value: string | {lat, lon}, gallons?: number } or null if invalid
 */
function parseAddressOrCoords(text) {
  const trimmed = (text || "").trim();
  if (!trimmed) return null;

  // Check for gallons separator " | "
  const parts = trimmed.split(/\s*\|\s*/);
  const mainPart = parts[0].trim();
  const gallonsPart = parts.length > 1 ? parts[1].trim() : null;
  const gallons = gallonsPart ? parseFloat(gallonsPart) : null;
  const validGallons = gallons !== null && !isNaN(gallons) && gallons >= 0 ? gallons : null;

  // Try to match lat,lon format
  const coordMatch = mainPart.match(/^([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)$/);
  if (coordMatch) {
    const lat = parseFloat(coordMatch[1]);
    const lon = parseFloat(coordMatch[2]);

    // Validate lat/lon ranges
    if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      const result = { type: 'coords', value: { lat, lon } };
      if (validGallons !== null) result.gallons = validGallons;
      return result;
    }
  }

  // Otherwise treat as address
  const result = { type: 'address', value: mainPart };
  if (validGallons !== null) result.gallons = validGallons;
  return result;
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
  
  // Show capacity usage if available
  let capacityInfo = "";
  if (driver.total_gallons !== undefined && driver.truck_capacity !== undefined) {
    const usage = ((driver.total_gallons / driver.truck_capacity) * 100).toFixed(1);
    const capacityClass = usage > 95 ? "warn" : "ok";
    capacityInfo = `<div class="small" style="margin-top:8px;">
      <span class="badge ${capacityClass}">Capacity: ${driver.total_gallons} / ${driver.truck_capacity} gallons (${usage}%)</span>
    </div>`;
  }

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
      ${capacityInfo}
      ${err}
      <details style="margin-top:8px;">
        <summary>Stops (${(driver.ordered_deliveries || []).length})</summary>
        <ol>${(driver.ordered_deliveries || []).map(s => {
          const stopText = typeof s === 'string' ? s : s.address || s;
          const stopGallons = typeof s === 'object' && s.gallons ? ` (${s.gallons} gal)` : '';
          return `<li>${escapeHtml(stopText)}${stopGallons}</li>`;
        }).join("")}</ol>
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

function addStopRow() {
  const tbody = $("stops-tbody");
  const rowCount = tbody.rows.length;
  const row = tbody.insertRow();
  row.innerHTML = `
    <td style="text-align: center; color: var(--muted);">${rowCount + 1}</td>
    <td><input type="text" class="table-input" placeholder="123 Main St, City, State ZIP" style="width: 100%;" /></td>
    <td><input type="number" class="table-input" placeholder="0" min="0" step="1" style="width: 100%; font-family: ui-monospace;" /></td>
    <td style="text-align: center;"><button type="button" class="btn small ghost" onclick="removeStopRow(this)" style="padding: 4px 8px;">×</button></td>
  `;
  updateRowNumbers();
}

function removeStopRow(btn) {
  const row = btn.closest("tr");
  row.remove();
  updateRowNumbers();
}

function updateRowNumbers() {
  const tbody = $("stops-tbody");
  Array.from(tbody.rows).forEach((row, index) => {
    row.cells[0].textContent = index + 1;
  });
}

const STORAGE_KEY = "oil_route_planner_data";

function getFormData() {
  const tbody = $("stops-tbody");
  const stops = [];
  for (let i = 0; i < tbody.rows.length; i++) {
    const row = tbody.rows[i];
    const addrInput = row.cells[1].querySelector("input");
    const gallonsInput = row.cells[2].querySelector("input");
    const address = (addrInput?.value || "").trim();
    if (!address) continue;
    const gallons = (gallonsInput?.value || "").trim();
    stops.push({ address, gallons: gallons || "0" });
  }
  return {
    depot: ($("depot").value || "").trim(),
    max_drivers: $("max_drivers").value || "6",
    max_stops_per_driver: $("max_stops_per_driver").value || "7",
    truck_capacity: $("truck_capacity").value || "2000",
    stops,
  };
}

function populateStopsTable(rows) {
  const tbody = $("stops-tbody");
  tbody.innerHTML = "";
  const data = Array.isArray(rows) && rows.length ? rows : [{ address: "", gallons: "" }];
  data.forEach((r, i) => {
    const row = tbody.insertRow();
    const addrCell = row.insertCell(0);
    addrCell.style.textAlign = "center";
    addrCell.style.color = "var(--muted)";
    addrCell.textContent = i + 1;
    const inputCell = row.insertCell(1);
    const addrInput = document.createElement("input");
    addrInput.type = "text";
    addrInput.className = "table-input";
    addrInput.value = r.address || "";
    addrInput.style.width = "100%";
    addrInput.placeholder = "123 Main St, City, State ZIP";
    inputCell.appendChild(addrInput);
    const gallonsCell = row.insertCell(2);
    const gallonsInput = document.createElement("input");
    gallonsInput.type = "number";
    gallonsInput.className = "table-input";
    gallonsInput.value = r.gallons != null && r.gallons !== "" ? String(r.gallons) : "";
    gallonsInput.min = "0";
    gallonsInput.step = "1";
    gallonsInput.style.width = "100%";
    gallonsInput.style.fontFamily = "ui-monospace";
    gallonsInput.placeholder = "0";
    gallonsCell.appendChild(gallonsInput);
    const deleteCell = row.insertCell(3);
    deleteCell.style.textAlign = "center";
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn small ghost";
    deleteBtn.textContent = "×";
    deleteBtn.style.padding = "4px 8px";
    deleteBtn.onclick = () => removeStopRow(deleteBtn);
    deleteCell.appendChild(deleteBtn);
  });
}

function setFormData(data) {
  if (!data || typeof data !== "object") return;
  if (data.depot != null) $("depot").value = data.depot;
  if (data.max_drivers != null) $("max_drivers").value = String(data.max_drivers);
  if (data.max_stops_per_driver != null) $("max_stops_per_driver").value = String(data.max_stops_per_driver);
  if (data.truck_capacity != null) $("truck_capacity").value = String(data.truck_capacity);
  if (Array.isArray(data.stops) && data.stops.length) {
    populateStopsTable(data.stops);
  }
}

function saveToLocalStorage() {
  try {
    const data = getFormData();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setStatus("Saved locally.");
    setTimeout(() => setStatus(""), 2000);
  } catch (e) {
    setStatus("Could not save: " + (e.message || "storage error"));
  }
}

function loadFromLocalStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const data = JSON.parse(raw);
    setFormData(data);
    setStatus("Loaded saved data.");
    setTimeout(() => setStatus(""), 2000);
    return true;
  } catch (e) {
    return false;
  }
}

function exportToCSV() {
  const data = getFormData();
  if (!data.stops.length) {
    setStatus("No stops to export.");
    setTimeout(() => setStatus(""), 2000);
    return;
  }
  const header = "address,gallons\n";
  const rows = data.stops.map((s) => {
    const addr = (s.address || "").replace(/"/g, '""');
    return `"${addr}",${s.gallons || "0"}`;
  });
  const csv = header + rows.join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "route_planner_stops_" + new Date().toISOString().slice(0, 10) + ".csv";
  a.click();
  URL.revokeObjectURL(a.href);
  setStatus("Exported to CSV.");
  setTimeout(() => setStatus(""), 2000);
}

function importFromCSV(file) {
  if (!file || !file.name) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const text = reader.result;
      const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
      if (!lines.length) {
        setStatus("CSV is empty.");
        setTimeout(() => setStatus(""), 2000);
        return;
      }
      const rows = [];
      const header = lines[0].toLowerCase();
      const hasHeader = /^\s*["']?(address|addr)["']?\s*[,;\t]|^\s*["']?address["']?\s*$/i.test(header) ||
        /^\s*["']?gallons?["']?\s*$/i.test(header) || header.startsWith("address") || header.startsWith("addr");
      const start = hasHeader ? 1 : 0;
      for (let i = start; i < lines.length; i++) {
        const line = lines[i];
        let address = "";
        let gallons = "";
        if (line.includes(",")) {
          const parts = line.match(/("(?:[^"]|"")*"|[^,]*)/g);
          if (parts && parts.length >= 1) {
            address = (parts[0] || "").replace(/^"|"$/g, "").replace(/""/g, '"').trim();
            gallons = (parts[1] || "").replace(/^"|"$/g, "").trim();
          }
        } else if (line.includes("\t")) {
          const parts = line.split("\t");
          address = (parts[0] || "").trim();
          gallons = (parts[1] || "").trim();
        } else {
          address = line;
        }
        if (address) rows.push({ address, gallons });
      }
      if (!rows.length) {
        setStatus("No valid rows in CSV.");
        setTimeout(() => setStatus(""), 2000);
        return;
      }
      populateStopsTable(rows);
      setStatus(`Imported ${rows.length} stops from CSV.`);
      setTimeout(() => setStatus(""), 2000);
    } catch (e) {
      setStatus("Import failed: " + (e.message || "parse error"));
    }
  };
  reader.readAsText(file, "UTF-8");
}

function fillDemo() {
  $("depot").value = "125 Broadway, Newburgh, NY 12550";
  
  const addresses = [
    "67 Howell Rd, Campbell Hall, NY 10916",
    "135 S Plank Rd, Newburgh, NY 12550",
    "8 North St, Montgomery, NY 12549",
    "45 Main St, Goshen, NY 10924",
    "100 Broadway, Newburgh, NY 12550",
    "234 Route 17M, Middletown, NY 10940",
    "12 Lake St, Monroe, NY 10950",
    "89 Main St, Warwick, NY 10990",
    "156 Route 32, Cornwall, NY 12518",
    "23 Washington St, Washingtonville, NY 10992",
    "78 Main St, Chester, NY 10918",
    "145 Route 94, Blooming Grove, NY 10914",
    "34 Union Ave, New Windsor, NY 12553",
    "67 Main St, Walden, NY 12586",
    "12 Main St, Highland Falls, NY 10928",
    "234 Route 17, Harriman, NY 10926",
    "45 Main St, Port Jervis, NY 12771",
    "123 Route 17K, Montgomery, NY 12549",
    "56 Toleman Rd, Goshen, NY 10924",
    "89 Route 6, Cornwall-on-Hudson, NY 12520",
    "234 Main St, Middletown, NY 10940",
    "12 Park Ave, Newburgh, NY 12550",
    "67 Liberty St, Newburgh, NY 12550",
    "145 Route 17M, Goshen, NY 10924",
    "34 Front St, Port Jervis, NY 12771",
    "78 Route 94, Washingtonville, NY 10992",
    "23 Main St, Monroe, NY 10950",
    "156 Route 17, Harriman, NY 10926",
    "89 Broadway, Newburgh, NY 12550",
    "234 Lake St, Monroe, NY 10950",
  ];
  
  const gallons = [
    "200", "300", "150", "400", "250",
    "600", "180", "350", "220", "280",
    "190", "450", "320", "210", "170",
    "380", "500", "240", "290", "160",
    "420", "330", "270", "360", "480",
    "230", "310", "390", "260", "340",
  ];
  
  // Clear existing rows
  const tbody = $("stops-tbody");
  tbody.innerHTML = "";
  
  // Add rows with data
  addresses.forEach((addr, i) => {
    const row = tbody.insertRow();
    const addrCell = row.insertCell(0);
    addrCell.style.textAlign = "center";
    addrCell.style.color = "var(--muted)";
    addrCell.textContent = i + 1;
    
    const inputCell = row.insertCell(1);
    const addrInput = document.createElement("input");
    addrInput.type = "text";
    addrInput.className = "table-input";
    addrInput.value = addr;
    addrInput.style.width = "100%";
    inputCell.appendChild(addrInput);
    
    const gallonsCell = row.insertCell(2);
    const gallonsInput = document.createElement("input");
    gallonsInput.type = "number";
    gallonsInput.className = "table-input";
    gallonsInput.value = gallons[i];
    gallonsInput.min = "0";
    gallonsInput.step = "1";
    gallonsInput.style.width = "100%";
    gallonsInput.style.fontFamily = "ui-monospace";
    gallonsCell.appendChild(gallonsInput);
    
    const deleteCell = row.insertCell(3);
    deleteCell.style.textAlign = "center";
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn small ghost";
    deleteBtn.textContent = "×";
    deleteBtn.style.padding = "4px 8px";
    deleteBtn.onclick = () => removeStopRow(deleteBtn);
    deleteCell.appendChild(deleteBtn);
  });
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
  // Load saved data on page load
  loadFromLocalStorage();
  
  $("fill-demo").addEventListener("click", fillDemo);
  $("add-stop-row").addEventListener("click", addStopRow);
  
  // Save/Load functionality
  $("save-local").addEventListener("click", saveToLocalStorage);
  $("export-csv").addEventListener("click", exportToCSV);
  $("import-csv").addEventListener("click", () => $("csv-file-input").click());
  $("csv-file-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      importFromCSV(file);
      e.target.value = ""; // Reset input
    }
  });
  
  // Make removeStopRow available globally
  window.removeStopRow = removeStopRow;

  $("plan-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    $("results").style.display = "none";
    $("error").style.display = "none";
    $("drivers").innerHTML = "";
    $("summary").innerHTML = "";

    const depot_input = $("depot").value.trim();
    const max_drivers = parseInt($("max_drivers").value, 10) || 6;
    const max_stops_per_driver = parseInt($("max_stops_per_driver").value, 10) || 7;
    const truck_capacity = parseFloat($("truck_capacity").value) || 2000;

    if (!depot_input) {
      $("error").style.display = "block";
      $("error").textContent = "Please provide depot address.";
      return;
    }

    // Parse depot
    const depotParsed = parseAddressOrCoords(depot_input);
    if (!depotParsed) {
      $("error").style.display = "block";
      $("error").textContent = "Invalid depot address/coordinates.";
      return;
    }

    // Parse stops from table
    const tbody = $("stops-tbody");
    const stops = [];
    for (let i = 0; i < tbody.rows.length; i++) {
      const row = tbody.rows[i];
      const addressInput = row.cells[1].querySelector("input");
      const gallonsInput = row.cells[2].querySelector("input");
      
      const addressValue = (addressInput?.value || "").trim();
      if (!addressValue) {
        continue; // Skip empty rows
      }
      
      // Parse address
      const parsed = parseAddressOrCoords(addressValue);
      if (!parsed) {
        $("error").style.display = "block";
        $("error").textContent = `Invalid address at row ${i + 1}: ${escapeHtml(addressValue)}`;
        return;
      }
      
      // Parse gallons
      const gallonsValue = (gallonsInput?.value || "").trim();
      if (gallonsValue) {
        const gallons = parseFloat(gallonsValue);
        if (!isNaN(gallons) && gallons >= 0) {
          parsed.gallons = gallons;
        }
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
        truck_capacity,
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
      const totalGallons = drivers.reduce((n, d) => n + (d.total_gallons || 0), 0);

      $("summary").innerHTML = `
        <div class="row wrap">
          <div><div class="small">Drivers</div><div class="mono">${drivers.length}</div></div>
          <div><div class="small">Total stops</div><div class="mono">${totalStops}</div></div>
          ${totalGallons > 0 ? `<div><div class="small">Total gallons</div><div class="mono">${totalGallons.toLocaleString()}</div></div>` : ''}
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
