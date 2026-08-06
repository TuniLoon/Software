/**
 * TuniLoon Dashboard JavaScript
 * Handles real-time updates, map, and graphs
 */

// ============================================================
// 1. CONFIGURATION
// ============================================================

const CONFIG = {
    API_BASE: '/api/telemetry',
    UPDATE_INTERVAL: 1000,  // 1 second
    MAX_HISTORY: 100,
    STATUS_COLORS: {
        'A': '#2196f3',
        'D': '#ff9800',
        'L': '#4caf50',
        'E': '#f44336',
        'F': '#9c27b0'
    }
};

// ============================================================
// 2. STATE
// ============================================================

let state = {
    data: [],
    latest: null,
    isDark: false,
    map: null,
    marker: null,
    path: [],
    altitudeGraph: null,
    temperatureGraph: null,
    isRunning: true,
    packetCounter: 0  // ADDED: separate packet counter
};

// ============================================================
// 3. DOM REFERENCES
// ============================================================

const DOM = {
    // Status
    statusBadge: document.getElementById('status-badge'),
    packetCount: document.getElementById('packet-count'),
    
    // Stats
    statAltitude: document.getElementById('stat-altitude'),
    statLatitude: document.getElementById('stat-latitude'),
    statLongitude: document.getElementById('stat-longitude'),
    statTemperature: document.getElementById('stat-temperature'),
    statPressure: document.getElementById('stat-pressure'),
    statStatus: document.getElementById('stat-status'),
    
    // Details
    detailTime: document.getElementById('detail-time'),
    detailAltitude: document.getElementById('detail-altitude'),
    detailLatitude: document.getElementById('detail-latitude'),
    detailLongitude: document.getElementById('detail-longitude'),
    detailTemperature: document.getElementById('detail-temperature'),
    detailPressure: document.getElementById('detail-pressure'),
    detailHumidity: document.getElementById('detail-humidity'),
    detailThermal: document.getElementById('detail-thermal'),
    detailStatus: document.getElementById('detail-status'),
    detailChecksum: document.getElementById('detail-checksum'),
    
    // Graph stats
    graphMaxAlt: document.getElementById('graph-max-alt'),
    graphMinTemp: document.getElementById('graph-min-temp'),
    graphMaxTemp: document.getElementById('graph-max-temp'),
    lastUpdated: document.getElementById('last-updated'),
    mapCoords: document.getElementById('map-coords'),
    
    // Buttons
    themeToggle: document.getElementById('theme-toggle'),
    clearBtn: document.getElementById('clear-btn')
};

// ============================================================
// 4. INITIALIZATION
// ============================================================

function init() {
    console.log('[Dashboard] Initializing...');
    
    initMap();
    initGraphs();
    initEventListeners();
    startDataPolling();
    updateStatus(true);
    updatePacketCount(0);  // Initialize packet count
    
    console.log('[Dashboard] Ready!');
}

// ============================================================
// 5. MAP
// ============================================================

function initMap() {
    // Center on Sousse, Tunisia
    const center = [35.8276, 10.6402];
    
    state.map = L.map('map').setView(center, 12);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(state.map);
    
    // Marker
    state.marker = L.circleMarker(center, {
        radius: 10,
        fillColor: '#ff6b35',
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(state.map);
    
    state.marker.bindPopup('TuniLoon Balloon');
    
    // Path
    state.path = L.polyline([], {
        color: '#ff6b35',
        weight: 3,
        opacity: 0.7
    }).addTo(state.map);
    
    updateMapCoords(center[0], center[1]);
}

function updateMap(lat, lon) {
    if (!state.map || !state.marker || !state.path) return;
    
    // Update marker position
    state.marker.setLatLng([lat, lon]);
    
    // Update path
    state.path.addLatLng([lat, lon]);
    
    // Center map on balloon
    state.map.setView([lat, lon], state.map.getZoom());
    
    // Update coordinates display
    updateMapCoords(lat, lon);
}

function updateMapCoords(lat, lon) {
    DOM.mapCoords.textContent = `Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}`;
}

// ============================================================
// 6. GRAPHS
// ============================================================

function initGraphs() {
    // Altitude graph
    const altDiv = document.getElementById('altitude-graph');
    state.altitudeGraph = Plotly.newPlot(altDiv, [{
        name: 'Altitude',
        x: [],
        y: [],
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: '#2196f3', width: 2 },
        marker: { color: '#2196f3', size: 4 }
    }], {
        margin: { l: 40, r: 10, t: 10, b: 30 },
        xaxis: { title: 'Time', showgrid: true, gridcolor: 'rgba(128,128,128,0.1)' },
        yaxis: { title: 'Altitude (m)', showgrid: true, gridcolor: 'rgba(128,128,128,0.1)' },
        plot_bgcolor: 'transparent',
        paper_bgcolor: 'transparent',
        font: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary') }
    });
    
    // Temperature graph
    const tempDiv = document.getElementById('temperature-graph');
    state.temperatureGraph = Plotly.newPlot(tempDiv, [{
        name: 'Temperature',
        x: [],
        y: [],
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: '#ff9800', width: 2 },
        marker: { color: '#ff9800', size: 4 }
    }], {
        margin: { l: 40, r: 10, t: 10, b: 30 },
        xaxis: { title: 'Time', showgrid: true, gridcolor: 'rgba(128,128,128,0.1)' },
        yaxis: { title: 'Temperature (°C)', showgrid: true, gridcolor: 'rgba(128,128,128,0.1)' },
        plot_bgcolor: 'transparent',
        paper_bgcolor: 'transparent',
        font: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary') }
    });
}

function updateGraphs(data) {
    if (!data || data.length === 0) return;
    
    const times = data.map(d => {
        const ts = new Date(d.timestamp);
        return ts.toLocaleTimeString();
    });
    
    const altitudes = data.map(d => d.altitude);
    const temperatures = data.map(d => d.temperature);
    
    // Update altitude graph
    Plotly.restyle('altitude-graph', {
        x: [times],
        y: [altitudes]
    });
    
    // Update temperature graph
    Plotly.restyle('temperature-graph', {
        x: [times],
        y: [temperatures]
    });
    
    // Update max altitude
    const maxAlt = Math.max(...altitudes);
    DOM.graphMaxAlt.textContent = maxAlt.toFixed(0);
    
    // Update min/max temperature
    const minTemp = Math.min(...temperatures);
    const maxTemp = Math.max(...temperatures);
    DOM.graphMinTemp.textContent = minTemp.toFixed(1);
    DOM.graphMaxTemp.textContent = maxTemp.toFixed(1);
}

// ============================================================
// 7. UI UPDATE FUNCTIONS
// ============================================================

function updateStatus(online) {
    DOM.statusBadge.textContent = online ? '● Online' : '● Offline';
    DOM.statusBadge.className = `badge ${online ? 'online' : 'offline'}`;
}

function updateStats(data) {
    if (!data) return;
    
    DOM.statAltitude.textContent = `${data.altitude.toFixed(0)} m`;
    DOM.statLatitude.textContent = data.latitude.toFixed(4);
    DOM.statLongitude.textContent = data.longitude.toFixed(4);
    DOM.statTemperature.textContent = `${data.temperature.toFixed(1)} °C`;
    DOM.statPressure.textContent = `${data.pressure.toFixed(1)} hPa`;
    
    // Status badge
    const statusMap = { 'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error', 'F': 'Cut-down' };
    const statusText = statusMap[data.status] || data.status;
    DOM.statStatus.textContent = statusText;
    DOM.statStatus.className = `stat-value status-badge status-${data.status}`;
}

function updateDetails(data) {
    if (!data) return;
    
    DOM.detailTime.textContent = new Date(data.timestamp).toLocaleString();
    DOM.detailAltitude.textContent = `${data.altitude.toFixed(0)} m`;
    DOM.detailLatitude.textContent = data.latitude.toFixed(6);
    DOM.detailLongitude.textContent = data.longitude.toFixed(6);
    DOM.detailTemperature.textContent = `${data.temperature.toFixed(1)} °C`;
    DOM.detailPressure.textContent = `${data.pressure.toFixed(1)} hPa`;
    DOM.detailHumidity.textContent = `${data.humidity.toFixed(1)} %`;
    DOM.detailThermal.textContent = `${data.thermal_avg.toFixed(1)} °C`;
    
    const statusMap = { 'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error', 'F': 'Cut-down' };
    DOM.detailStatus.textContent = statusMap[data.status] || data.status;
    DOM.detailChecksum.textContent = data.checksum;
    
    DOM.lastUpdated.textContent = `Last update: ${new Date(data.timestamp).toLocaleTimeString()}`;
}

function updatePacketCount(count) {
    state.packetCounter = count;
    DOM.packetCount.textContent = `Packets: ${count}`;
}

// ============================================================
// 8. DATA POLLING
// ============================================================

function startDataPolling() {
    fetchLatest();
    fetchHistory();
    
    setInterval(() => {
        if (!state.isRunning) return;
        fetchLatest();
        fetchHistory();
    }, CONFIG.UPDATE_INTERVAL);
}

async function fetchLatest() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/latest`);
        const data = await response.json();
        
        if (data) {
            state.latest = data;
            updateStats(data);
            updateDetails(data);
            updateMap(data.latitude, data.longitude);
            // Increment packet counter when new data arrives
            updatePacketCount(state.packetCounter + 1);
            updateStatus(true);
        }
    } catch (error) {
        console.error('[Dashboard] Error fetching latest:', error);
        updateStatus(false);
    }
}

async function fetchHistory() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/history?limit=${CONFIG.MAX_HISTORY}`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            state.data = data;
            updateGraphs(data);
        }
    } catch (error) {
        console.error('[Dashboard] Error fetching history:', error);
    }
}

// ============================================================
// 9. EVENT LISTENERS
// ============================================================

function initEventListeners() {
    // Theme toggle
    DOM.themeToggle.addEventListener('click', toggleTheme);
    
    // Clear button
    DOM.clearBtn.addEventListener('click', clearData);
}

function toggleTheme() {
    state.isDark = !state.isDark;
    document.documentElement.setAttribute('data-theme', state.isDark ? 'dark' : 'light');
    DOM.themeToggle.innerHTML = state.isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    
    // Redraw graphs with new theme colors
    updateGraphs(state.data);
}

async function clearData() {
    if (!confirm('Clear all telemetry data?')) return;
    
    try {
        await fetch(`${CONFIG.API_BASE}/clear`);
        state.data = [];
        state.latest = null;
        state.packetCounter = 0;  // Reset packet counter
        
        // Clear the path on the map
        if (state.map) {
            state.path = L.polyline([], {
                color: '#ff6b35',
                weight: 3,
                opacity: 0.7
            }).addTo(state.map);
        }
        
        // Clear graphs
        updateGraphs([]);
        
        // Reset stats display
        DOM.statAltitude.textContent = '0 m';
        DOM.statLatitude.textContent = '0.0000';
        DOM.statLongitude.textContent = '0.0000';
        DOM.statTemperature.textContent = '0.0 °C';
        DOM.statPressure.textContent = '0.0 hPa';
        DOM.statStatus.textContent = '—';
        DOM.statStatus.className = 'stat-value status-badge';
        
        // Reset details
        DOM.detailTime.textContent = '—';
        DOM.detailAltitude.textContent = '—';
        DOM.detailLatitude.textContent = '—';
        DOM.detailLongitude.textContent = '—';
        DOM.detailTemperature.textContent = '—';
        DOM.detailPressure.textContent = '—';
        DOM.detailHumidity.textContent = '—';
        DOM.detailThermal.textContent = '—';
        DOM.detailStatus.textContent = '—';
        DOM.detailChecksum.textContent = '—';
        DOM.lastUpdated.textContent = 'Last update: —';
        
        // Update packet count to 0
        updatePacketCount(0);
        
        updateStatus(true);
        console.log('[Dashboard] Data cleared');
    } catch (error) {
        console.error('[Dashboard] Error clearing data:', error);
    }
}

// ============================================================
// 10. STARTUP
// ============================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
