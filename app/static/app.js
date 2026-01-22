function $(id) { return document.getElementById(id); }

function linesToStops(text) {
  return text
    .split(/\r?\n/)
    .map(s => s.trim())
    .filter(s => s.length > 0)
    .map(addr => ({ address: addr }));
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

function renderScheduleTable(schedule) {
  const rows = (schedule || []).map((r, i) => {
    const notes = Array.isArray(r.notes) ? r.notes.join("; ") : (r.notes || "");
    const window = r.window || "";
    return `
      <tr>
        <td>${i}</td>
        <td>${escapeHtml(r.type || "")}</td>
        <td class="mono">${escapeHtml(r.eta || "")}</td>
        <td class="mono">${escapeHtml(window)}</td>
        <td>${escapeHtml(r.address || "")}</td>
        <td>${escapeHtml(notes)}</td>
      </tr>
    `;
  }).join("");
  return `
    <table class="table">
      <thead>
        <tr>
          <th>#</th><th>Type</th><th>ETA</th><th>30-min window</th><th>Address</th><th>Notes</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function driverCard(driver) {
  const ok = !!driver.feasible;
  const badge = ok ? `<span class="badge ok">Feasible</span>` : `<span class="badge warn">Not feasible</span>`;
  const link = driver.google_maps_link
    ? `<a class="btn link" href="${driver.google_maps_link}" target="_blank" rel="noreferrer">Open in Google Maps</a>`
    : "";
  const err = driver.error ? `<div class="error" style="margin-top:8px;">${escapeHtml(driver.error)}</div>` : "";
  const sched = ok ? renderScheduleTable(driver.schedule) : "";

  return `
    <section class="card" style="margin-top:12px;">
      <div class="row-between">
        <h3 style="margin:0;">${escapeHtml(driver.driver || "Driver")}</h3>
        <div>${badge}</div>
      </div>
      <div class="row wrap" style="margin-top:8px;">
        <div>
          <div class="small">Lunch</div>
          <div class="mono">${escapeHtml(driver.lunch || "")}</div>
        </div>
        <div>${link}</div>
      </div>
      ${err}
      ${sched}
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
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  $("date").value = `${yyyy}-${mm}-${dd}`;
  $("departure_time").value = window.DEFAULT_DEPARTURE || "07:00";
  $("depot").value = "1 Depot Rd, Newburgh, NY 12550";
  $("stops_bulk").value = [
    "67 Howell Rd, Campbell Hall, NY 10916",
    "135 S Plank Rd, Newburgh, NY 12550",
    "8 North St, Montgomery, NY 12549",
    "45 Main St, Goshen, NY 10924",
    "100 Broadway, Newburgh, NY 12550",
  ].join("\n");
}

window.addEventListener("DOMContentLoaded", () => {
  $("fill-demo").addEventListener("click", fillDemo);

  $("plan-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    $("results").style.display = "none";
    $("error").style.display = "none";
    $("unassigned").style.display = "none";
    $("drivers").innerHTML = "";
    $("summary").innerHTML = "";

    const date = $("date").value;
    const depot_address = $("depot").value.trim();
    const departure_time = $("departure_time").value;
    const stops = linesToStops($("stops_bulk").value);

    const body = {
      date,
      departure_time,
      depot_address,
      stops,
      default_service_minutes: parseInt($("service_minutes").value, 10),

      work_window_start: $("work_start").value,
      work_window_end: $("work_end").value,
      lunch_window_start: $("lunch_start").value,
      lunch_window_end: $("lunch_end").value,
      lunch_minutes: parseInt($("lunch_minutes").value, 10),
      lunch_skippable: $("lunch_skippable").checked,

      max_drivers: parseInt($("max_drivers").value, 10),
      max_stops_per_driver: parseInt($("max_stops_per_driver").value, 10),
    };

    if (!depot_address || !date || stops.length === 0) {
      $("error").style.display = "block";
      $("error").textContent = "Please provide date, depot address, and at least one stop.";
      return;
    }

    setStatus("Planning...");
    $("plan-btn").disabled = true;

    try {
      const res = await postJSON("/api/plan_multi", body);
      if (!res.json) {
        throw new Error(`Non-JSON response (HTTP ${res.status}): ${res.text.slice(0, 300)}`);
      }

      const data = res.json;
      
      // Debug logging
      console.log("API Response:", data);
      console.log("data.feasible:", data.feasible);
      console.log("data.drivers:", data.drivers);
      console.log("data.routes:", data.routes);
      console.log("data.drivers_used:", data.drivers_used);

      $("results").style.display = "block";

      if (!data.feasible) {
        $("error").style.display = "block";
        $("error").textContent = data.error || "No feasible plan.";
      }

      const drivers = data.drivers || data.routes || [];
      $("summary").innerHTML = `
        <div class="row wrap">
          <div><div class="small">Drivers used</div><div class="mono">${drivers.length}</div></div>
          <div><div class="small">Total stops</div><div class="mono">${stops.length}</div></div>
        </div>
      `;

      $("drivers").innerHTML = drivers.map(driverCard).join("");

      if (Array.isArray(data.unassigned) && data.unassigned.length > 0) {
        $("unassigned").style.display = "block";
        $("unassigned").innerHTML = "<strong>Unassigned stops:</strong><br/>" + data.unassigned.map(escapeHtml).join("<br/>");
      }

      setStatus("");
    } catch (err) {
      $("results").style.display = "block";
      $("error").style.display = "block";
      $("error").textContent = err?.message || String(err);
      setStatus("");
    } finally {
      $("plan-btn").disabled = false;
    }
  });
});
