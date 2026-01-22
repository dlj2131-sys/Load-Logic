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

function driverCard(driver) {
  const ok = !!driver.feasible;
  const badge = ok ? `<span class="badge ok">Feasible</span>` : `<span class="badge warn">Not feasible</span>`;
  const link = driver.google_maps_link
    ? `<a class="btn link" href="${driver.google_maps_link}" target="_blank" rel="noreferrer">Open in Google Maps</a>`
    : "";
  const err = driver.error ? `<div class="error" style="margin-top:8px;">${escapeHtml(driver.error)}</div>` : "";

  return `
    <section class="card" style="margin-top:12px;">
      <div class="row-between">
        <h3 style="margin:0;">${escapeHtml(driver.driver || "Driver")}</h3>
        <div>${badge}</div>
      </div>
      <div class="row wrap" style="margin-top:8px;">
        <div>${link}</div>
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
  $("depot").value = "1 Depot Rd, Newburgh, NY 12550";
  $("stops_bulk").value = [
    "67 Howell Rd, Campbell Hall, NY 10916",
    "135 S Plank Rd, Newburgh, NY 12550",
    "8 North St, Montgomery, NY 12549",
    "45 Main St, Goshen, NY 10924",
    "100 Broadway, Newburgh, NY 12550",
    "40.7580,-73.9855",
    "40.7489,-73.9680",
  ].join("\n");
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
      `;

      $("drivers").innerHTML = drivers.map(driverCard).join("");
      $("results").style.display = "block";
      $("results").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      $("plan-btn").disabled = false;
      setStatus("");
      $("results").style.display = "block";
      $("error").style.display = "block";
      $("error").textContent = err?.message || String(err);
    }
  });
});
