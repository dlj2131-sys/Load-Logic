/**
 * Owner Dashboard
 * Manages delivery requests and route creation
 */

let requests = [];
let routes = [];
let selectedRequests = new Set();
let currentFilter = 'pending';

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    refreshRequests();
    refreshRoutes();
    setInterval(refreshRequests, 30000); // Refresh every 30 seconds
    setInterval(refreshRoutes, 30000);
});

async function refreshRequests() {
    try {
        const res = await fetch(`/api/requests?status=${currentFilter === 'all' ? '' : currentFilter}`);
        const data = await res.json();

        requests = data.requests || [];
        renderRequests();
    } catch (err) {
        console.error('Error loading requests:', err);
    }
}

async function refreshRoutes() {
    try {
        const res = await fetch('/api/routes');
        const data = await res.json();

        routes = data.routes || [];
        renderRoutes();
    } catch (err) {
        console.error('Error loading routes:', err);
    }
}

function renderRequests() {
    const list = document.getElementById('requests-list');

    if (requests.length === 0) {
        list.innerHTML = '<div class="empty-state">No requests found</div>';
        return;
    }

    let html = `
        <table class="requests-table">
            <thead>
                <tr>
                    <th><input type="checkbox" id="select-all" onchange="toggleSelectAll(this)"></th>
                    <th>Customer</th>
                    <th>Address</th>
                    <th>Fuel</th>
                    <th>Qty</th>
                    <th>Status</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
    `;

    requests.forEach(req => {
        const statusClass = `status-${req.status}`;
        html += `
            <tr class="request-row" onclick="toggleRequest('${req.id}')">
                <td><input type="checkbox" class="checkbox" ${selectedRequests.has(req.id) ? 'checked' : ''} onchange="toggleRequest('${req.id}')"></td>
                <td>${escapeHtml(req.customer_name)}</td>
                <td>${escapeHtml(req.delivery_address.substring(0, 30))}...</td>
                <td>${escapeHtml(req.fuel_type)}</td>
                <td>${req.order_quantity_gallons}</td>
                <td><span class="status-badge ${statusClass}">${req.status}</span></td>
                <td>${req.requested_delivery_date || '—'}</td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    list.innerHTML = html;
    updateBatchControls();
}

function renderRoutes() {
    const list = document.getElementById('routes-list');
    const activeRoutes = routes.filter(r => r.status === 'active');

    if (activeRoutes.length === 0) {
        list.innerHTML = '<div class="empty-state">No active routes</div>';
        return;
    }

    let html = '';
    activeRoutes.forEach(route => {
        html += `
            <div class="route-card">
                <div class="route-info">
                    <h4>Route ${route.id}</h4>
                    <p>Driver: ${route.driver_id}</p>
                    <p>Stops: ${route.stops.length}</p>
                </div>
                <div class="route-actions">
                    <a href="/driver/route/${route.id}" target="_blank">View Driver Portal</a>
                </div>
            </div>
        `;
    });

    list.innerHTML = html;
}

function toggleRequest(requestId) {
    if (selectedRequests.has(requestId)) {
        selectedRequests.delete(requestId);
    } else {
        selectedRequests.add(requestId);
    }
    updateBatchControls();
}

function toggleSelectAll(checkbox) {
    if (checkbox.checked) {
        requests.forEach(req => selectedRequests.add(req.id));
    } else {
        selectedRequests.clear();
    }
    renderRequests();
}

function updateBatchControls() {
    const batchControls = document.getElementById('batch-controls');
    const selectedCount = document.getElementById('selected-count');

    selectedCount.textContent = selectedRequests.size;

    if (selectedRequests.size > 0) {
        batchControls.classList.add('show');
    } else {
        batchControls.classList.remove('show');
    }
}

function filterStatus(status) {
    currentFilter = status;
    refreshRequests();
}

function openBatchModal() {
    document.getElementById('batch-modal').classList.add('show');
}

function closeBatchModal() {
    document.getElementById('batch-modal').classList.remove('show');
}

async function submitBatchRouting() {
    const depotAddress = document.getElementById('depot-address').value.trim();
    const maxDrivers = parseInt(document.getElementById('max-drivers').value) || 6;
    const maxStops = parseInt(document.getElementById('max-stops').value) || 7;

    if (!depotAddress) {
        alert('Please enter a depot address');
        return;
    }

    if (selectedRequests.size === 0) {
        alert('Please select at least one request');
        return;
    }

    const button = event.target;
    button.disabled = true;
    button.textContent = 'Creating routes...';

    try {
        const res = await fetch('/api/requests/batch-to-routes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_ids: Array.from(selectedRequests),
                depot_address: depotAddress,
                max_drivers: maxDrivers,
                max_stops_per_driver: maxStops
            })
        });

        const json = await res.json();

        if (res.ok && json.success) {
            alert(`Success! Created ${json.routes.length} route(s)\n\nRoutes have been assigned to drivers.`);
            selectedRequests.clear();
            closeBatchModal();
            refreshRequests();
            refreshRoutes();
        } else {
            alert(`Error: ${json.error || 'Failed to create routes'}`);
        }
    } catch (err) {
        alert('Error creating routes. Please try again.');
        console.error(err);
    } finally {
        button.disabled = false;
        button.textContent = 'Create Routes';
    }
}

function escapeHtml(str) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return (str || '').replace(/[&<>"']/g, m => map[m]);
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('batch-modal');
    if (e.target === modal) {
        closeBatchModal();
    }
});
