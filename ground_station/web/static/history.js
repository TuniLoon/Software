/**
 * TuniLoon Flight History – Robust Version
 */

let allFlights = [];

async function loadFlights() {
    const container = document.getElementById('flight-list');
    container.innerHTML = '<div class="no-flights">Loading flights...</div>';
    try {
        console.log('[History] Fetching /api/history/list');
        const response = await fetch('/api/history/list');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        console.log('[History] Received data:', data);
        allFlights = data;
        renderFlights(data);
    } catch (e) {
        console.error('[History] Error:', e);
        container.innerHTML = '<div class="no-flights">Error loading flights. Check console.</div>';
    }
}

function renderFlights(flights) {
    const container = document.getElementById('flight-list');
    if (!flights || flights.length === 0) {
        container.innerHTML = '<div class="no-flights">No flights found. Simulate a flight to generate data.</div>';
        return;
    }

    let html = `
        <table class="flight-table">
            <thead>
                <tr>
                    <th><input type="checkbox" id="select-all"></th>
                    <th>Flight ID</th>
                    <th>Start Time</th>
                    <th>Duration (min)</th>
                    <th>Max Altitude (m)</th>
                    <th>Packets</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
    `;

    flights.forEach(f => {
        const duration = f.duration ? Math.round(f.duration / 60) : '?';
        html += `
            <tr>
                <td><input type="checkbox" class="flight-check" value="${f.id}"></td>
                <td>${f.id}</td>
                <td>${f.start_time ? new Date(f.start_time).toLocaleString() : '—'}</td>
                <td>${duration}</td>
                <td>${f.max_altitude ? f.max_altitude.toFixed(0) : '—'}</td>
                <td>${f.packet_count || '—'}</td>
                <td>
                    <button class="btn-pdf" data-flight-id="${f.id}">
                        <i class="fas fa-file-pdf"></i> PDF
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;

    // Add select-all event
    document.getElementById('select-all').addEventListener('change', function() {
        document.querySelectorAll('.flight-check').forEach(cb => cb.checked = this.checked);
    });

    // Add PDF button event listeners
    document.querySelectorAll('.btn-pdf[data-flight-id]').forEach(btn => {
        btn.addEventListener('click', function() {
            const flightId = this.getAttribute('data-flight-id');
            window.location.href = `/api/history/report/${flightId}`;
        });
    });

    // Add compare button (if not already present)
    if (!document.getElementById('compare-btn')) {
        const btn = document.createElement('button');
        btn.id = 'compare-btn';
        btn.className = 'btn-pdf';
        btn.style.background = '#ff6b35';
        btn.textContent = '📊 Compare Selected';
        btn.addEventListener('click', function() {
            const selected = document.querySelectorAll('.flight-check:checked');
            const ids = Array.from(selected).map(cb => cb.value);
            if (ids.length < 2) {
                alert('Select at least 2 flights to compare.');
                return;
            }
            window.location.href = '/compare?ids=' + ids.join(',');
        });
        const filterRow = document.querySelector('.filter-row');
        if (filterRow) {
            filterRow.appendChild(btn);
        } else {
            container.parentNode.insertBefore(btn, container);
        }
    }
}

function downloadReport(flightId) {
    window.location.href = `/api/history/report/${flightId}`;
}

// Filter functionality
function applyFilters() {
    const dateFilter = document.getElementById('filter-date').value.toLowerCase();
    const minAlt = parseFloat(document.getElementById('filter-alt-min').value) || 0;
    const maxAlt = parseFloat(document.getElementById('filter-alt-max').value) || Infinity;

    const filtered = allFlights.filter(f => {
        const dateMatch = f.start_time ? f.start_time.toLowerCase().includes(dateFilter) : true;
        const altMatch = (f.max_altitude || 0) >= minAlt && (f.max_altitude || 0) <= maxAlt;
        return dateMatch && altMatch;
    });
    renderFlights(filtered);
}

// Add event listeners after DOM ready
document.getElementById('filter-date')?.addEventListener('input', applyFilters);
document.getElementById('filter-alt-min')?.addEventListener('input', applyFilters);
document.getElementById('filter-alt-max')?.addEventListener('input', applyFilters);
document.getElementById('clear-filters')?.addEventListener('click', function() {
    document.getElementById('filter-date').value = '';
    document.getElementById('filter-alt-min').value = '';
    document.getElementById('filter-alt-max').value = '';
    renderFlights(allFlights);
});

// Load flights on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadFlights);
} else {
    loadFlights();
}
