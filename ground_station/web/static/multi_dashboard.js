/**
 * TuniLoon Multi-Balloon Dashboard
 */

// ============================================================
// State
// ============================================================

const state = {
    balloons: {},        // id -> balloon data
    map: null,
    markers: {},         // id -> Leaflet marker
    paths: {},           // id -> Leaflet polyline
    pathVisible: true,
    selectedBalloon: null,
    isDark: false,
    updateInterval: null,
    colors: [
        '#ff6b35', '#00c853', '#2196f3', '#ff9800', '#9c27b0',
        '#f44336', '#4caf50', '#3f51b5', '#ff5722', '#009688',
        '#e91e63', '#8bc34a', '#00bcd4', '#ffc107', '#795548'
    ]
};

// ============================================================
// DOM References
// ============================================================

const DOM = {
    status: document.getElementById('status-badge'),
    balloonList: document.getElementById('balloon-list'),
    balloonCount: document.getElementById('balloon-count'),
    sidebarCount: document.getElementById('sidebar-count'),
    themeToggle: document.getElementById('theme-toggle'),
};

// ============================================================
// Initialization
// ============================================================

function init() {
    console.log('[Multi] Initializing multi-balloon dashboard...');
    initMap();
    initWeather();
    initEventListeners();
    startDataPolling();
    setTimeout(addDemoBalloons, 1000);
    console.log('[Multi] Ready!');
}

// ============================================================
// Map
// ============================================================

function initMap() {
    const center = [34.7400, 10.7600];
    state.map = L.map('map').setView(center, 10);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19
    }).addTo(state.map);
}

function addMarker(balloonId, data) {
    const { latitude, longitude, altitude } = data;
    
    if (state.markers[balloonId]) {
        state.map.removeLayer(state.markers[balloonId]);
    }
    
    const color = state.balloons[balloonId].color || '#ff6b35';
    const popupContent = createPopupContent(balloonId);
    
    const marker = L.circleMarker([latitude, longitude], {
        radius: 10,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(state.map);
    
    marker.bindPopup(popupContent);
    marker.on('click', () => selectBalloon(balloonId));
    
    state.markers[balloonId] = marker;
    
    updatePath(balloonId, { latitude, longitude });
}

function updatePath(balloonId, pos) {
    if (!state.paths[balloonId]) {
        const color = state.balloons[balloonId].color || '#ff6b35';
        state.paths[balloonId] = L.polyline([], {
            color: color,
            weight: 2,
            opacity: 0.5
        }).addTo(state.map);
    }
    state.paths[balloonId].addLatLng([pos.latitude, pos.longitude]);
    
    if (!state.pathVisible) {
        state.paths[balloonId].setStyle({ opacity: 0 });
    }
}

function resetMapView() {
    const center = [34.7400, 10.7600];
    state.map.setView(center, 10);
}

function toggleAllPaths() {
    state.pathVisible = !state.pathVisible;
    Object.values(state.paths).forEach(path => {
        path.setStyle({ opacity: state.pathVisible ? 0.5 : 0 });
    });
}

function createPopupContent(balloonId) {
    const b = state.balloons[balloonId];
    if (!b) return '<div>No data</div>';
    const latest = b.latest || {};
    return `
        <div class="balloon-detail-popup">
            <div class="title" style="color:${b.color}">${b.name}</div>
            <div class="detail-row"><span>Altitude</span><span>${(latest.altitude || 0).toFixed(0)} m</span></div>
            <div class="detail-row"><span>Temperature</span><span>${(latest.temperature || 0).toFixed(1)} °C</span></div>
            <div class="detail-row"><span>Status</span><span>${b.statusText || 'Unknown'}</span></div>
            <div class="detail-row"><span>Last Update</span><span>${b.lastUpdate || '—'}</span></div>
        </div>
    `;
}

function selectBalloon(balloonId) {
    state.selectedBalloon = balloonId;
    renderBalloonList();
}

// ============================================================
// Balloon Management
// ============================================================

function addBalloon(balloonId, name) {
    if (state.balloons[balloonId]) {
        console.log(`[Multi] Balloon ${balloonId} already exists, skipping`);
        return;
    }
    
    const colorIndex = Object.keys(state.balloons).length % state.colors.length;
    state.balloons[balloonId] = {
        id: balloonId,
        name: name || `Balloon-${balloonId.slice(0,6)}`,
        color: state.colors[colorIndex],
        latest: null,
        history: [],
        statusText: 'Unknown',
        lastUpdate: null,
        active: true
    };
    
    renderBalloonList();
    updateCounts();
    console.log(`[Multi] Added balloon: ${balloonId}`);
}

function updateBalloon(balloonId, data) {
    if (!state.balloons[balloonId]) {
        addBalloon(balloonId, data.name);
    }
    
    const b = state.balloons[balloonId];
    b.latest = data;
    b.lastUpdate = new Date().toLocaleTimeString();
    b.statusText = getStatusText(data.status);
    b.history.push(data);
    if (b.history.length > 200) b.history.shift();
    
    if (data.latitude && data.longitude) {
        addMarker(balloonId, data);
    }
    
    renderBalloonList();
    updateCounts();
}

function removeBalloon(balloonId) {
    if (state.markers[balloonId]) {
        state.map.removeLayer(state.markers[balloonId]);
        delete state.markers[balloonId];
    }
    if (state.paths[balloonId]) {
        state.map.removeLayer(state.paths[balloonId]);
        delete state.paths[balloonId];
    }
    delete state.balloons[balloonId];
    renderBalloonList();
    updateCounts();
}

function clearAllBalloons() {
    if (!confirm('Remove all balloons?')) return;
    Object.keys(state.balloons).forEach(id => removeBalloon(id));
}

function getStatusText(status) {
    const map = { 'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error', 'F': 'Cut-down' };
    return map[status] || status || 'Unknown';
}

function updateCounts() {
    const count = Object.keys(state.balloons).length;
    DOM.balloonCount.textContent = `Balloons: ${count}`;
    DOM.sidebarCount.textContent = count;
}

// ============================================================
// Demo Data Generation (Fixed)
// ============================================================

function addDemoBalloons() {
    console.log('[Multi] Adding demo balloons...');
    
    // First, remove any existing demo balloons with the same IDs
    const demoIds = ['TUN001', 'TUN002', 'TUN003', 'TUN004'];
    demoIds.forEach(id => {
        if (state.balloons[id]) {
            console.log(`[Multi] Removing existing demo balloon ${id}`);
            removeBalloon(id);
        }
    });

    // Now add fresh ones
    const demos = [
        { id: 'TUN001', name: 'TuniLoon-1', lat: 34.7400, lon: 10.7600, alt: 15000, temp: -35, status: 'A' },
        { id: 'TUN002', name: 'TuniLoon-2', lat: 34.8000, lon: 10.8200, alt: 8000, temp: -10, status: 'A' },
        { id: 'TUN003', name: 'TuniLoon-3', lat: 34.6800, lon: 10.7000, alt: 0, temp: 25, status: 'L' },
        { id: 'TUN004', name: 'TuniLoon-4', lat: 34.9000, lon: 10.9000, alt: 22000, temp: -50, status: 'A' },
    ];
    
    demos.forEach(d => {
        addBalloon(d.id, d.name);
        updateBalloon(d.id, {
            latitude: d.lat,
            longitude: d.lon,
            altitude: d.alt,
            temperature: d.temp,
            status: d.status
        });
    });
    
    console.log('[Multi] Added 4 demo balloons');
}

// ============================================================
// Render Functions
// ============================================================

function renderBalloonList() {
    const items = Object.values(state.balloons);
    if (items.length === 0) {
        DOM.balloonList.innerHTML = `
            <div style="padding:20px; text-align:center; color: var(--text-secondary);">
                No balloons active<br>
                <small>Click "Add Demo" or wait for real data</small>
            </div>
        `;
        return;
    }
    
    DOM.balloonList.innerHTML = items.map(b => `
        <div class="multi-balloon-item ${state.selectedBalloon === b.id ? 'active' : ''}"
             onclick="selectBalloon('${b.id}')" data-id="${b.id}">
            <div class="multi-balloon-color" style="background:${b.color}"></div>
            <div class="multi-balloon-info">
                <div class="multi-balloon-name">${b.name}</div>
                <div class="multi-balloon-altitude">
                    ${b.latest ? `${(b.latest.altitude || 0).toFixed(0)}m | ${b.latest.temperature ? b.latest.temperature.toFixed(1) + '°C' : ''}` : 'Waiting...'}
                </div>
            </div>
            <span class="multi-balloon-status balloon-status-${b.latest?.status || 'U'}">${b.statusText}</span>
        </div>
    `).join('');
}

// ============================================================
// Data Polling
// ============================================================

function startDataPolling() {
    let counter = 0;
    state.updateInterval = setInterval(() => {
        Object.values(state.balloons).forEach(b => {
            if (b.latest && b.latest.latitude) {
                const lat = b.latest.latitude + (Math.random() - 0.5) * 0.001;
                const lon = b.latest.longitude + (Math.random() - 0.5) * 0.001;
                const alt = b.latest.altitude + (Math.random() - 0.5) * 50;
                const statuses = ['A', 'A', 'A', 'D', 'D', 'L'];
                const status = statuses[Math.floor(Math.random() * statuses.length)];
                
                updateBalloon(b.id, {
                    latitude: lat,
                    longitude: lon,
                    altitude: Math.max(0, alt),
                    temperature: 25 - alt * 0.0065,
                    status: status
                });
            }
        });
        counter++;
    }, 2000);
}

// ============================================================
// Event Listeners
// ============================================================

function initEventListeners() {
    DOM.themeToggle.addEventListener('click', () => {
        state.isDark = !state.isDark;
        document.documentElement.setAttribute('data-theme', state.isDark ? 'dark' : 'light');
        DOM.themeToggle.innerHTML = state.isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    });
}

// ============================================================
// Startup
// ============================================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Make functions globally accessible
window.addDemoBalloons = addDemoBalloons;
window.resetMapView = resetMapView;
window.toggleAllPaths = toggleAllPaths;
window.clearAllBalloons = clearAllBalloons;
window.selectBalloon = selectBalloon;
