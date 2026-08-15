/**
 * TuniLoon Dashboard – HTTP Polling (No WebSockets)
 */

const CONFIG = {
    API_BASE: '/api/telemetry',
    UPDATE_INTERVAL: 1000,
    MAX_HISTORY: 100
};

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
    packetCounter: 0
};

const DOM = {
    statusBadge: document.getElementById('status-badge'),
    packetCount: document.getElementById('packet-count'),
    statAltitude: document.getElementById('stat-altitude'),
    statLatitude: document.getElementById('stat-latitude'),
    statLongitude: document.getElementById('stat-longitude'),
    statTemperature: document.getElementById('stat-temperature'),
    statPressure: document.getElementById('stat-pressure'),
    statStatus: document.getElementById('stat-status'),
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
    graphMaxAlt: document.getElementById('graph-max-alt'),
    graphMinTemp: document.getElementById('graph-min-temp'),
    graphMaxTemp: document.getElementById('graph-max-temp'),
    lastUpdated: document.getElementById('last-updated'),
    mapCoords: document.getElementById('map-coords'),
    themeToggle: document.getElementById('theme-toggle'),
    clearBtn: document.getElementById('clear-btn')
};

function init() {
    console.log('[Dashboard] Initializing...');
    createProgressBar();
    initMap();
    initGraphs();
    initEventListeners();
    startDataPolling();
    updateStatus(true);
    updatePacketCount(0);
    console.log('[Dashboard] Ready!');
}

// ------------------------- Map -------------------------
function initMap() {
    const center = [35.8276, 10.6402];
    state.map = L.map('map').setView(center, 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19
    }).addTo(state.map);
    state.marker = L.circleMarker(center, {
        radius: 10,
        fillColor: '#ff6b35',
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(state.map);
    state.marker.bindPopup('TuniLoon Balloon');
    state.path = L.polyline([], { color: '#ff6b35', weight: 3, opacity: 0.7 }).addTo(state.map);
    updateMapCoords(center[0], center[1]);
}

function updateMap(lat, lon) {
    if (!state.map || !state.marker || !state.path) return;
    if (lat === 0 && lon === 0) return;
    state.marker.setLatLng([lat, lon]);
    state.path.addLatLng([lat, lon]);
    state.map.setView([lat, lon], state.map.getZoom());
    updateMapCoords(lat, lon);
}

function updateMapCoords(lat, lon) {
    DOM.mapCoords.textContent = `Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}`;
}

// ------------------------- Graphs -------------------------
function initGraphs() {
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
        font: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary') || '#333' }
    });
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
        font: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary') || '#333' }
    });
}

function updateGraphs(data) {
    if (!data || data.length === 0) return;
    data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const times = data.map(d => new Date(d.timestamp).toLocaleTimeString());
    const altitudes = data.map(d => d.altitude || 0);
    const temperatures = data.map(d => d.temperature || 0);

    const altDiv = document.getElementById('altitude-graph');
    Plotly.react(altDiv, [{
        name: 'Altitude',
        x: times,
        y: altitudes,
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: '#2196f3', width: 2 },
        marker: { color: '#2196f3', size: 4 }
    }], state.altitudeGraph.layout);

    Plotly.restyle('temperature-graph', {
        x: [times],
        y: [temperatures]
    });

    const maxAlt = Math.max(...altitudes);
    DOM.graphMaxAlt.textContent = maxAlt.toFixed(0);
    const minTemp = Math.min(...temperatures);
    const maxTemp = Math.max(...temperatures);
    DOM.graphMinTemp.textContent = minTemp.toFixed(1);
    DOM.graphMaxTemp.textContent = maxTemp.toFixed(1);

    const anomalyIndices = data.map((d, i) => d.anomaly ? i : null).filter(i => i !== null);
    if (anomalyIndices.length > 0) {
        const anomalyTimes = anomalyIndices.map(i => times[i]);
        const anomalyAlts = anomalyIndices.map(i => altitudes[i]);
        Plotly.addTraces('altitude-graph', {
            x: anomalyTimes,
            y: anomalyAlts,
            mode: 'markers',
            type: 'scatter',
            marker: { color: 'red', size: 12, symbol: 'x' },
            name: 'Anomaly'
        });
    }
}

// ------------------------- UI Update Functions -------------------------
function updateStatus(online) {
    DOM.statusBadge.textContent = online ? '● Online' : '● Offline';
    DOM.statusBadge.className = `badge ${online ? 'online' : 'offline'}`;
}

function updateStats(data) {
    if (!data) return;
    DOM.statAltitude.textContent = `${(data.altitude || 0).toFixed(0)} m`;
    DOM.statLatitude.textContent = (data.latitude || 0).toFixed(4);
    DOM.statLongitude.textContent = (data.longitude || 0).toFixed(4);
    DOM.statTemperature.textContent = `${(data.temperature || 0).toFixed(1)} °C`;
    DOM.statPressure.textContent = `${(data.pressure || 0).toFixed(1)} hPa`;
    const statusMap = { 'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error', 'F': 'Cut-down' };
    const statusText = statusMap[data.status] || data.status || '—';
    DOM.statStatus.textContent = statusText;
    DOM.statStatus.className = `stat-value status-badge status-${data.status || 'U'}`;
    if (data.anomaly) {
        DOM.statStatus.style.backgroundColor = '#ffcccc';
        DOM.statStatus.textContent += ' ⚠️';
    } else {
        DOM.statStatus.style.backgroundColor = '';
    }
    updateProgress(data.altitude);
}

function updateDetails(data) {
    if (!data) return;
    DOM.detailTime.textContent = data.timestamp ? new Date(data.timestamp).toLocaleString() : '—';
    DOM.detailAltitude.textContent = `${(data.altitude || 0).toFixed(0)} m`;
    DOM.detailLatitude.textContent = (data.latitude || 0).toFixed(6);
    DOM.detailLongitude.textContent = (data.longitude || 0).toFixed(6);
    DOM.detailTemperature.textContent = `${(data.temperature || 0).toFixed(1)} °C`;
    DOM.detailPressure.textContent = `${(data.pressure || 0).toFixed(1)} hPa`;
    DOM.detailHumidity.textContent = `${(data.humidity || 0).toFixed(1)} %`;
    DOM.detailThermal.textContent = `${(data.thermal_avg || 0).toFixed(1)} °C`;
    const statusMap = { 'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error', 'F': 'Cut-down' };
    DOM.detailStatus.textContent = statusMap[data.status] || data.status || '—';
    DOM.detailChecksum.textContent = data.checksum || '—';
    DOM.lastUpdated.textContent = data.timestamp ? `Last update: ${new Date(data.timestamp).toLocaleTimeString()}` : 'Last update: —';
}

function updatePacketCount(count) {
    state.packetCounter = count;
    DOM.packetCount.textContent = `Packets: ${count}`;
}

function updateProgress(altitude) {
    const maxAltitude = 30000;
    const percent = Math.min((altitude / maxAltitude) * 100, 100);
    const progressBar = document.getElementById('flight-progress');
    const percentLabel = document.getElementById('progress-percent');
    if (progressBar) progressBar.style.width = percent + '%';
    if (percentLabel) percentLabel.textContent = Math.round(percent) + '%';
}

// ------------------------- HTTP Polling -------------------------
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
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && data.latitude && data.longitude) {
            state.latest = data;
            updateStats(data);
            updateDetails(data);
            updateMap(data.latitude, data.longitude);
            updatePacketCount(state.packetCounter + 1);
            updateStatus(true);
        } else {
            console.warn('[Dashboard] No valid data in latest response');
        }
    } catch (error) {
        console.error('[Dashboard] Error fetching latest:', error);
        updateStatus(false);
    }
}

async function fetchHistory() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/history?limit=${CONFIG.MAX_HISTORY}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && Array.isArray(data) && data.length > 0) {
            state.data = data;
            updateGraphs(data);
        }
    } catch (error) {
        console.error('[Dashboard] Error fetching history:', error);
    }
}

// ------------------------- Event Listeners -------------------------
function initEventListeners() {
    DOM.themeToggle.addEventListener('click', toggleTheme);
    DOM.clearBtn.addEventListener('click', clearData);
    document.getElementById('export-kml')?.addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = '/api/export/kml';
    });
    document.getElementById('export-gpx')?.addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = '/api/export/gpx';
    });
    const speedBtn = document.getElementById('toggle-speed');
    if (speedBtn) {
        speedBtn.addEventListener('click', function() {
            const isRealTime = this.classList.toggle('active');
            fetch('/api/sim/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({real_time: isRealTime})
            })
            .then(response => response.json())
            .then(data => {
                console.log('Speed mode:', data.real_time ? 'real-time' : 'fast');
                this.innerHTML = isRealTime ? '⏱️' : '⏩';
            })
            .catch(err => console.error('Toggle error:', err));
        });
    }
}

function toggleTheme() {
    state.isDark = !state.isDark;
    document.documentElement.setAttribute('data-theme', state.isDark ? 'dark' : 'light');
    DOM.themeToggle.innerHTML = state.isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    updateGraphs(state.data);
}

async function clearData() {
    if (!confirm('Clear all telemetry data?')) return;
    try {
        await fetch(`${CONFIG.API_BASE}/clear`);
        state.data = [];
        state.latest = null;
        state.packetCounter = 0;
        if (state.map) {
            state.path = L.polyline([], { color: '#ff6b35', weight: 3, opacity: 0.7 }).addTo(state.map);
        }
        updateGraphs([]);
        updatePacketCount(0);
        DOM.statAltitude.textContent = '0 m';
        DOM.statLatitude.textContent = '0.0000';
        DOM.statLongitude.textContent = '0.0000';
        DOM.statTemperature.textContent = '0.0 °C';
        DOM.statPressure.textContent = '0.0 hPa';
        DOM.statStatus.textContent = '—';
        DOM.statStatus.className = 'stat-value status-badge';
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
        DOM.graphMaxAlt.textContent = '0';
        DOM.graphMinTemp.textContent = '0.0';
        DOM.graphMaxTemp.textContent = '0.0';
        updateProgress(0);
        updateStatus(true);
    } catch (error) {
        console.error('[Dashboard] Error clearing data:', error);
    }
}

function createProgressBar() {
    const old = document.getElementById('progress-container');
    if (old) old.remove();
    const container = document.createElement('div');
    container.id = 'progress-container';
    container.style.margin = '10px 16px';
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-size: 13px; color: var(--text-secondary);">
            <span>Flight Progress</span>
            <span id="progress-percent">0%</span>
        </div>
        <div style="background: var(--bg-primary); border-radius: 8px; overflow: hidden; height: 12px; width: 100%;">
            <div id="flight-progress" style="width: 0%; background: linear-gradient(90deg, #ff6b35, #ff9800); height: 100%; transition: width 0.5s;"></div>
        </div>
    `;
    const statsBar = document.querySelector('.stats-bar');
    if (statsBar) {
        statsBar.parentNode.insertBefore(container, statsBar.nextSibling);
    } else {
        document.body.prepend(container);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
