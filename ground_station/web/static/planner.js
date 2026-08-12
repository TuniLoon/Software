/**
 * TuniLoon Flight Planner
 */

let map;
let marker;
let pathLine;
let landingMarker;
let isSimulating = false;

function initPlanner() {
    // Set default launch time to now + 1 hour
    const now = new Date();
    now.setHours(now.getHours() + 1);
    const iso = now.toISOString().slice(0, 16);
    document.getElementById('launch-time').value = iso;

    // Initialize map
    const center = [35.8276, 10.6402];
    map = L.map('map').setView(center, 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19
    }).addTo(map);

    // Click on map to set launch site
    map.on('click', function(e) {
        const lat = e.latlng.lat.toFixed(6);
        const lon = e.latlng.lng.toFixed(6);
        document.getElementById('launch-coords').value = `${lat}, ${lon}`;
        updateLaunchMarker(lat, lon);
    });

    // Initial marker
    updateLaunchMarker(35.8276, 10.6402);

    // Simulate button
    document.getElementById('simulate-btn').addEventListener('click', runSimulation);
}

function updateLaunchMarker(lat, lon) {
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon], { draggable: true })
        .addTo(map)
        .bindPopup('Launch Site');
    marker.on('dragend', function(e) {
        const pos = marker.getLatLng();
        document.getElementById('launch-coords').value = `${pos.lat.toFixed(6)}, ${pos.lng.toFixed(6)}`;
    });
    map.setView([lat, lon], 12);
}

async function runSimulation() {
    if (isSimulating) return;
    isSimulating = true;
    const btn = document.getElementById('simulate-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating...';

    // Get params
    const coords = document.getElementById('launch-coords').value.split(',').map(s => parseFloat(s.trim()));
    if (coords.length !== 2 || isNaN(coords[0]) || isNaN(coords[1])) {
        alert('Invalid coordinates. Use format: lat, lon');
        resetButton();
        return;
    }
    const lat = coords[0];
    const lon = coords[1];
    const launchTime = document.getElementById('launch-time').value;
    if (!launchTime) {
        alert('Please select a launch time');
        resetButton();
        return;
    }

    try {
        const response = await fetch('/api/planner/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lon, launch_time: launchTime })
        });
        const data = await response.json();
        if (data.error) {
            alert('Error: ' + data.error);
            resetButton();
            return;
        }
        displayResults(data);
        drawPath(data.trajectory);
    } catch (e) {
        console.error(e);
        alert('Simulation failed: ' + e.message);
    }
    resetButton();
}

function resetButton() {
    const btn = document.getElementById('simulate-btn');
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-rocket"></i> Simulate';
    isSimulating = false;
}

function displayResults(data) {
    document.getElementById('result-box').style.display = 'block';
    document.getElementById('landing-lat').textContent = data.landing_lat.toFixed(6);
    document.getElementById('landing-lon').textContent = data.landing_lon.toFixed(6);
    document.getElementById('duration').textContent = Math.round(data.duration / 60) + ' min';
    document.getElementById('max-alt').textContent = data.max_altitude.toFixed(0) + ' m';

    if (landingMarker) map.removeLayer(landingMarker);
    landingMarker = L.marker([data.landing_lat, data.landing_lon], {
        icon: L.divIcon({ className: 'landing-marker', html: '🛬', iconSize: [24, 24] })
    }).addTo(map).bindPopup('Predicted Landing');
}

function drawPath(trajectory) {
    if (pathLine) map.removeLayer(pathLine);
    const points = trajectory.map(p => [p.latitude, p.longitude]);
    pathLine = L.polyline(points, {
        color: '#ff6b35',
        weight: 3,
        opacity: 0.8,
        dashArray: '8 4'
    }).addTo(map);
    map.fitBounds(pathLine.getBounds(), { padding: [30, 30] });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPlanner);
} else {
    initPlanner();
}
