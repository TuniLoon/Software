/**
 * TuniLoon Flight Replay
 */

let replayData = [];
let currentIndex = 0;
let isPlaying = false;
let playTimer = null;
let speed = 1;
let map = null;
let marker = null;
let path = null;
let altitudeGraph = null;
let temperatureGraph = null;

// DOM refs
const DOM = {
    fileInput: document.getElementById('csv-file'),
    loadBtn: document.getElementById('load-btn'),
    fileStatus: document.getElementById('file-status'),
    playBtn: document.getElementById('play-btn'),
    pauseBtn: document.getElementById('pause-btn'),
    stopBtn: document.getElementById('stop-btn'),
    speedSlider: document.getElementById('speed-slider'),
    speedLabel: document.getElementById('speed-label'),
    progressText: document.getElementById('progress-text'),
    progressFill: document.getElementById('progress-fill'),
    progressPercent: document.getElementById('progress-percent'),
    statAltitude: document.getElementById('stat-altitude'),
    statLatitude: document.getElementById('stat-latitude'),
    statLongitude: document.getElementById('stat-longitude'),
    statTemperature: document.getElementById('stat-temperature'),
    statPressure: document.getElementById('stat-pressure'),
    statStatus: document.getElementById('stat-status'),
    detailTime: document.getElementById('detail-time'),
    detailAlt: document.getElementById('detail-alt'),
    detailLat: document.getElementById('detail-lat'),
    detailLon: document.getElementById('detail-lon'),
    detailTemp: document.getElementById('detail-temp'),
    detailPress: document.getElementById('detail-press'),
    detailHum: document.getElementById('detail-hum'),
    detailStatus: document.getElementById('detail-status'),
};

function initMap() {
    const center = [35.8276, 10.6402];
    map = L.map('map').setView(center, 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19
    }).addTo(map);
    marker = L.circleMarker(center, {
        radius: 10,
        fillColor: '#ff6b35',
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(map);
    marker.bindPopup('Balloon');
    path = L.polyline([], { color: '#ff6b35', weight: 3, opacity: 0.7 }).addTo(map);
}

function initGraphs() {
    const altDiv = document.getElementById('altitude-graph');
    altitudeGraph = Plotly.newPlot(altDiv, [{
        name: 'Altitude',
        x: [],
        y: [],
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: '#2196f3', width: 2 },
        marker: { color: '#2196f3', size: 4 }
    }], {
        margin: { l: 40, r: 10, t: 10, b: 30 },
        xaxis: { title: 'Time', showgrid: true },
        yaxis: { title: 'Altitude (m)', showgrid: true }
    });
    const tempDiv = document.getElementById('temperature-graph');
    temperatureGraph = Plotly.newPlot(tempDiv, [{
        name: 'Temperature',
        x: [],
        y: [],
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: '#ff9800', width: 2 },
        marker: { color: '#ff9800', size: 4 }
    }], {
        margin: { l: 40, r: 10, t: 10, b: 30 },
        xaxis: { title: 'Time', showgrid: true },
        yaxis: { title: 'Temperature (°C)', showgrid: true }
    });
}

function updateUI(index) {
    const point = replayData[index];
    if (!point) return;
    // Stats
    DOM.statAltitude.textContent = point.altitude.toFixed(0) + ' m';
    DOM.statLatitude.textContent = point.latitude.toFixed(4);
    DOM.statLongitude.textContent = point.longitude.toFixed(4);
    DOM.statTemperature.textContent = point.temperature.toFixed(1) + ' °C';
    DOM.statPressure.textContent = point.pressure.toFixed(1) + ' hPa';
    const statusMap = { 'A': 'Ascent', 'D': 'Descent', 'L': 'Landing' };
    DOM.statStatus.textContent = statusMap[point.status] || point.status;
    // Details
    DOM.detailTime.textContent = point.timestamp || '—';
    DOM.detailAlt.textContent = point.altitude.toFixed(0) + ' m';
    DOM.detailLat.textContent = point.latitude.toFixed(6);
    DOM.detailLon.textContent = point.longitude.toFixed(6);
    DOM.detailTemp.textContent = point.temperature.toFixed(1) + ' °C';
    DOM.detailPress.textContent = point.pressure.toFixed(1) + ' hPa';
    DOM.detailHum.textContent = point.humidity ? point.humidity.toFixed(1) + ' %' : '—';
    DOM.detailStatus.textContent = statusMap[point.status] || point.status;
    // Map
    marker.setLatLng([point.latitude, point.longitude]);
    path.addLatLng([point.latitude, point.longitude]);
    map.setView([point.latitude, point.longitude], map.getZoom());
    // Progress
    const progress = (index + 1) / replayData.length;
    DOM.progressFill.style.width = (progress * 100) + '%';
    DOM.progressPercent.textContent = Math.round(progress * 100) + '%';
    DOM.progressText.textContent = `${index + 1} / ${replayData.length}`;
    // Graphs – update all points up to current index
    const times = replayData.slice(0, index + 1).map((d, i) => i);
    const alts = replayData.slice(0, index + 1).map(d => d.altitude);
    const temps = replayData.slice(0, index + 1).map(d => d.temperature);
    Plotly.restyle('altitude-graph', { x: [times], y: [alts] });
    Plotly.restyle('temperature-graph', { x: [times], y: [temps] });
}

function loadCSV(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const lines = e.target.result.split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        replayData = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            if (values.length < 2) continue;
            const point = {};
            headers.forEach((h, idx) => {
                const val = values[idx];
                if (h === 'timestamp') point[h] = val;
                else if (h === 'status' || h === 'status_description') point[h] = val;
                else if (!isNaN(val)) point[h] = parseFloat(val);
                else point[h] = val;
            });
            // Ensure required fields
            if (point.altitude !== undefined && point.latitude !== undefined && point.longitude !== undefined) {
                // Default missing fields
                point.temperature = point.temperature || 25 - point.altitude * 0.0065;
                point.pressure = point.pressure || 1013 * Math.exp(-point.altitude / 8000);
                point.status = point.status || 'A';
                replayData.push(point);
            }
        }
        if (replayData.length === 0) {
            alert('No valid data found in CSV.');
            return;
        }
        DOM.fileStatus.textContent = `Loaded ${replayData.length} points`;
        currentIndex = 0;
        // Reset map path
        path.setLatLngs([]);
        // Initial update
        updateUI(0);
        // Enable controls
        DOM.playBtn.disabled = false;
        DOM.stopBtn.disabled = false;
        DOM.pauseBtn.disabled = true;
    };
    reader.readAsText(file);
}

function play() {
    if (isPlaying) return;
    if (currentIndex >= replayData.length - 1) {
        // Restart
        currentIndex = 0;
        path.setLatLngs([]);
    }
    isPlaying = true;
    DOM.playBtn.disabled = true;
    DOM.pauseBtn.disabled = false;
    const interval = 1000 / speed;
    playTimer = setInterval(() => {
        if (currentIndex >= replayData.length - 1) {
            stop();
            return;
        }
        currentIndex++;
        updateUI(currentIndex);
    }, interval);
}

function pause() {
    if (!isPlaying) return;
    isPlaying = false;
    clearInterval(playTimer);
    DOM.playBtn.disabled = false;
    DOM.pauseBtn.disabled = true;
}

function stop() {
    isPlaying = false;
    clearInterval(playTimer);
    currentIndex = 0;
    path.setLatLngs([]);
    if (replayData.length) updateUI(0);
    DOM.playBtn.disabled = false;
    DOM.pauseBtn.disabled = true;
    DOM.progressFill.style.width = '0%';
    DOM.progressPercent.textContent = '0%';
    DOM.progressText.textContent = `0 / ${replayData.length}`;
}

// Event listeners
DOM.loadBtn.addEventListener('click', function() {
    const file = DOM.fileInput.files[0];
    if (!file) { alert('Select a CSV file first.'); return; }
    loadCSV(file);
});

DOM.playBtn.addEventListener('click', play);
DOM.pauseBtn.addEventListener('click', pause);
DOM.stopBtn.addEventListener('click', stop);

DOM.speedSlider.addEventListener('input', function() {
    speed = parseFloat(this.value);
    DOM.speedLabel.textContent = speed + 'x';
    if (isPlaying) {
        // Restart timer with new speed
        pause();
        play();
    }
});

// Initialize
initMap();
initGraphs();
DOM.playBtn.disabled = true;
DOM.pauseBtn.disabled = true;
DOM.stopBtn.disabled = true;
console.log('[Replay] Ready');
