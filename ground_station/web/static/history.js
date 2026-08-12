/**
 * TuniLoon Flight History
 */

let allFlights = [];

async function loadFlights() {
    try {
        const response = await fetch('/api/history/list');
        const data = await response.json();
        allFlights = data;
        renderFlights(data);
    } catch (e) {
        console.error(e);
        document.getElementById('flight-list').innerHTML = '<div class="no-flights">Error loading flights</div>';
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
                <td>${f.id}</td>
                <td>${f.start_time ? new Date(f.start_time).toLocaleString() : '—'}</td>
                <td>${duration}</td>
                <td>${f.max_altitude ? f.max_altitude.toFixed(0) : '—'}</td>
                <td>${f.packet_count || '—'}</td>
                <td>
                    <button class="btn-pdf" onclick="downloadReport('${f.id}')">
                        <i class="fas fa-file-pdf"></i> PDF
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
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

document.getElementById('filter-date').addEventListener('input', applyFilters);
document.getElementById('filter-alt-min').addEventListener('input', applyFilters);
document.getElementById('filter-alt-max').addEventListener('input', applyFilters);
document.getElementById('clear-filters').addEventListener('click', function() {
    document.getElementById('filter-date').value = '';
    document.getElementById('filter-alt-min').value = '';
    document.getElementById('filter-alt-max').value = '';
    renderFlights(allFlights);
});

loadFlights();
