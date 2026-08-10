let weatherInterval = null;
let weatherData = {};
let weatherControlDiv = null;
let weatherRetryCount = 0;
const MAX_WEATHER_RETRIES = 5;

function initWeather() {
    console.log('[Weather] Initializing weather control...');
    const control = L.control({ position: 'bottomright' });
    control.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'weather-control');
        div.innerHTML = `
            <div id="weather-panel" style="background:white; padding:10px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.2); font-size:13px; min-width:160px;">
                <b>🌤️ Weather</b><br>
                <span id="weather-info">⏳ Loading...</span>
            </div>
        `;
        weatherControlDiv = div;
        console.log('[Weather] Control added to map');
        return div;
    };
    control.addTo(state.map);

    // First attempt after 1 second (to give demos time)
    setTimeout(fetchWeather, 1000);
    weatherInterval = setInterval(fetchWeather, 600000);
}

async function fetchWeather() {
    console.log('[Weather] Fetch triggered...');

    // Try to get coordinates from different state structures
    let lat, lon;

    if (state.latest && state.latest.latitude) {
        lat = state.latest.latitude;
        lon = state.latest.longitude;
        console.log('[Weather] Using state.latest');
    } else if (state.balloons) {
        const ids = Object.keys(state.balloons);
        if (ids.length > 0) {
            const firstBalloon = state.balloons[ids[0]];
            if (firstBalloon && firstBalloon.latest) {
                lat = firstBalloon.latest.latitude;
                lon = firstBalloon.latest.longitude;
                console.log('[Weather] Using first balloon position');
            }
        }
    }

    if (!lat || !lon) {
        console.warn('[Weather] No position available');
        if (weatherRetryCount < MAX_WEATHER_RETRIES) {
            weatherRetryCount++;
            console.log(`[Weather] Retry ${weatherRetryCount}/${MAX_WEATHER_RETRIES} in 2s...`);
            setTimeout(fetchWeather, 2000);
        } else {
            console.log('[Weather] Max retries reached, giving up');
            const infoEl = document.getElementById('weather-info');
            if (infoEl) infoEl.innerHTML = '❌ No position';
        }
        return;
    }

    // Reset retry count on success
    weatherRetryCount = 0;

    // Cache check (5 min)
    if (weatherData.timestamp && (Date.now() - weatherData.timestamp) < 300000) {
        console.log('[Weather] Using cached data');
        return;
    }

    const infoEl = document.getElementById('weather-info');
    if (infoEl) infoEl.innerHTML = '⏳ Fetching...';

    try {
        const url = `/api/weather/current?lat=${lat}&lon=${lon}`;
        console.log('[Weather] Fetching', url);
        const response = await fetch(url);
        const data = await response.json();
        console.log('[Weather] Data received:', data);

        if (data && data.main) {
            const temp = data.main.temp;
            const pressure = data.main.pressure;
            const humidity = data.main.humidity;
            const wind = data.wind ? `${data.wind.speed} m/s` : 'N/A';
            const desc = data.weather[0].description;
            if (infoEl) {
                infoEl.innerHTML = `
                    ${desc}<br>
                    🌡️ ${temp}°C  💨 ${wind}<br>
                    💧 ${humidity}%  📊 ${pressure} hPa
                `;
            }
            weatherData.timestamp = Date.now();
            console.log('[Weather] Updated successfully');
        } else {
            console.warn('[Weather] No main data in response');
            if (infoEl) infoEl.innerHTML = '❌ No data';
        }
    } catch (e) {
        console.error('[Weather] Fetch error:', e);
        if (infoEl) infoEl.innerHTML = '❌ Error';
    }
}
