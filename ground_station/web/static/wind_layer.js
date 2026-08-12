/**
 * TuniLoon Wind & Trajectory Layer
 */

let windMarker = null;
let predictedPath = null;
let windArrow = null;

function updateWindLayer(data) {
    if (!state.map) return;
    
    // Remove old wind arrow
    if (windArrow) {
        state.map.removeLayer(windArrow);
        windArrow = null;
    }
    if (predictedPath) {
        state.map.removeLayer(predictedPath);
        predictedPath = null;
    }
    
    const lat = data.latitude;
    const lon = data.longitude;
    const speed = data.speed || 0;
    const direction = data.direction || 0;
    
    // Draw wind arrow (Leaflet marker with custom rotation)
    const arrowLength = Math.min(30, speed * 3 + 10);
    const angle = direction - 90; // Convert to Leaflet angle
    const icon = L.divIcon({
        html: `
            <div style="transform: rotate(${angle}deg); text-align: center; font-size: ${arrowLength}px; line-height: 1; color: #ff6b35;">
                ↑
            </div>
        `,
        iconSize: [30, 30],
        className: 'wind-arrow'
    });
    windArrow = L.marker([lat, lon], { icon: icon }).addTo(state.map);
    windArrow.bindPopup(`Wind: ${speed.toFixed(1)} m/s from ${direction.toFixed(0)}°`);
}

function drawPredictedPath(trajectory) {
    if (!state.map || !trajectory || trajectory.length === 0) return;
    
    if (predictedPath) {
        state.map.removeLayer(predictedPath);
    }
    
    const points = trajectory.map(p => [p.latitude, p.longitude]);
    predictedPath = L.polyline(points, {
        color: '#ff6b35',
        weight: 3,
        opacity: 0.6,
        dashArray: '8 4'
    }).addTo(state.map);
    
    // Add landing marker
    const last = trajectory[trajectory.length - 1];
    L.marker([last.latitude, last.longitude], {
        icon: L.divIcon({ 
            className: 'landing-marker', 
            html: '🛬', 
            iconSize: [24, 24] 
        })
    }).addTo(state.map).bindPopup('Predicted Landing');
}

// Expose to dashboard.js
window.updateWindLayer = updateWindLayer;
window.drawPredictedPath = drawPredictedPath;
