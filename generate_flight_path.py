"""
TuniLoon - Sprint 0.4
Mock High-Altitude Balloon Flight Path Generator

Produces a physically-plausible (not meteorologically forecasted) 2-hour
flight profile for a balloon launched from central Tunisia, including:
  - constant-rate ascent
  - altitude-dependent parachute descent (terminal velocity grows with
    altitude because air density drops)
  - altitude-dependent wind drift (a simplified, hand-authored wind
    profile standing in for a real jet-stream / stratospheric reversal
    pattern -- NOT a live forecast)

Outputs:
  data/flight_path.csv     -> time_s, lat, lon, alt_m, phase   (the ask)
  data/sample_flight.csv   -> full TUN,... telemetry packets, one per row
  payload_simulator/config/flight_profile.json -> reusable model params
"""

import json
import math
import os
import numpy as np
import pandas as pd

# ---------------------------------------------------------------
# 1. Flight parameters
# ---------------------------------------------------------------

LAUNCH_LAT = 35.6781      # Kairouan, Tunisia (inland launch site)
LAUNCH_LON = 10.0963
LAUNCH_ALT = 65.0         # m ASL, ground elevation at launch site

BURST_ALTITUDE = 30000.0  # m
ASCENT_RATE = 5.8         # m/s, roughly constant with a small fill-dependent variance

DT = 10                   # seconds between samples
R_EARTH = 6371000.0       # m

# Altitude-banded wind model: (alt_m, speed_m_s, heading_deg)
# heading = compass direction the wind is BLOWING TOWARDS (0=N, 90=E, 180=S, 270=W)
# Loosely mimics: light easterly drift near the surface, a strong jet-stream
# band around 9-10 km, and a stratospheric wind reversal above ~20 km.
WIND_TABLE = [
    (0,     4.0,  95),
    (1000,  6.0,  90),
    (3000,  10.0, 85),
    (6000,  22.0, 80),
    (9000,  35.0, 75),
    (12000, 28.0, 90),
    (16000, 14.0, 110),
    (20000, 8.0,  160),
    (25000, 12.0, 220),
    (30000, 18.0, 240),
]
WIND_ALTS = np.array([w[0] for w in WIND_TABLE])
WIND_SPD = np.array([w[1] for w in WIND_TABLE])
WIND_HDG = np.array([w[2] for w in WIND_TABLE])

# Descent model (terminal velocity under parachute, grows with altitude
# as air density falls): v(h) = V0 * exp(h / (2*H)), H = atmospheric scale height
DESCENT_V0 = 5.0          # m/s, terminal velocity at sea level
SCALE_HEIGHT = 7000.0     # m

RNG = np.random.default_rng(42)  # fixed seed -> reproducible "mock" flight


def wind_at(alt_m):
    """Interpolated (speed_m_s, heading_deg) at a given altitude."""
    speed = float(np.interp(alt_m, WIND_ALTS, WIND_SPD))
    heading = float(np.interp(alt_m, WIND_ALTS, WIND_HDG))
    return speed, heading


def drift_step(lat, lon, alt_m, dt):
    """Advance lat/lon by dt seconds of wind drift at the current altitude."""
    speed, heading = wind_at(alt_m)
    # small turbulence jitter so the track isn't perfectly smooth
    speed *= 1.0 + RNG.normal(0, 0.05)
    heading += RNG.normal(0, 3.0)

    hdg_rad = math.radians(heading)
    v_north = speed * math.cos(hdg_rad)
    v_east = speed * math.sin(hdg_rad)

    dlat = (v_north * dt / R_EARTH) * (180.0 / math.pi)
    dlon = (v_east * dt / (R_EARTH * math.cos(math.radians(lat)))) * (180.0 / math.pi)
    return lat + dlat, lon + dlon


def descent_rate(alt_m):
    return DESCENT_V0 * math.exp(alt_m / (2 * SCALE_HEIGHT))


# ---------------------------------------------------------------
# 2. Simulate ascent
# ---------------------------------------------------------------

rows = []
t = 0.0
lat, lon, alt = LAUNCH_LAT, LAUNCH_LON, LAUNCH_ALT

while alt < BURST_ALTITUDE:
    rows.append((t, lat, lon, alt, "ascent"))
    alt = min(alt + ASCENT_RATE * DT, BURST_ALTITUDE)
    lat, lon = drift_step(lat, lon, alt, DT)
    t += DT

# Burst point (cut-down / balloon pop)
rows.append((t, lat, lon, alt, "burst"))
burst_t = t

# ---------------------------------------------------------------
# 3. Simulate descent
# ---------------------------------------------------------------

while alt > 0:
    v = descent_rate(alt)
    step_down = min(v * DT, alt)
    alt -= step_down
    lat, lon = drift_step(lat, lon, alt, DT)
    t += DT
    phase = "landing" if alt < 100 else "descent"
    rows.append((t, lat, lon, max(alt, 0.0), phase))

# ---------------------------------------------------------------
# 4. Build the requested flight_path.csv
# ---------------------------------------------------------------

df = pd.DataFrame(rows, columns=["time_s", "lat", "lon", "alt_m", "phase"])
df["lat"] = df["lat"].round(6)
df["lon"] = df["lon"].round(6)
df["alt_m"] = df["alt_m"].round(1)

os.makedirs("data", exist_ok=True)
df.to_csv("data/flight_path.csv", index=False)

print(f"Total flight time: {t/60:.1f} min "
      f"(ascent {burst_t/60:.1f} min, descent {(t-burst_t)/60:.1f} min)")
print(f"Rows: {len(df)}")
print(f"Landing point: {df.iloc[-1]['lat']}, {df.iloc[-1]['lon']}")
straight_line_km = R_EARTH * math.radians(
    math.hypot(df.iloc[-1]['lat'] - LAUNCH_LAT,
               (df.iloc[-1]['lon'] - LAUNCH_LON) * math.cos(math.radians(LAUNCH_LAT)))
) / 1000
print(f"Approx. straight-line drift from launch: {straight_line_km:.1f} km")

# ---------------------------------------------------------------
# 5. Build full telemetry packets (sample_flight.csv) matching the
#    Sprint 0.3 protocol: TUN,lat,lon,alt,press,temp,hum,thermal,checksum,status
# ---------------------------------------------------------------

def pressure_hpa(alt_m):
    # Standard barometric formula (troposphere/stratosphere blend, simplified)
    return 1013.25 * math.exp(-alt_m / 8434.0)


def temperature_c(alt_m):
    # Rough standard-atmosphere lapse: -6.5C/km up to ~11km, isothermal
    # ~ -56.5C from 11-20km, slight warming above due to ozone layer.
    if alt_m <= 11000:
        return 15.0 - 6.5 * (alt_m / 1000.0)
    elif alt_m <= 20000:
        return -56.5
    else:
        return -56.5 + 1.0 * ((alt_m - 20000) / 1000.0)


def humidity_pct(alt_m):
    # Humidity collapses fast with altitude; near-zero above the troposphere
    return max(2.0, 45.0 * math.exp(-alt_m / 3000.0))


def thermal_c(alt_m, ground_temp_c=32.0):
    # MLX90640 looks down at the ground; roughly tracks ground temp with
    # a small correction for haze/altitude while still low, then flat.
    if alt_m < 3000:
        return ground_temp_c - alt_m / 3000.0 * 4.0
    return ground_temp_c - 4.0 + RNG.normal(0, 0.3)


def checksum(lat, lon, alt, press, temp, hum, thermal):
    return int(
        (int(lat * 10000) + int(lon * 10000) + int(alt) +
         int(press * 10) + int(temp * 10) + int(hum * 10) +
         int(thermal * 10))
    ) % 10000


STATUS_MAP = {"ascent": "A", "burst": "F", "descent": "D", "landing": "L"}

# inject one brief GPS-loss ("E") window during descent for realism/testing
error_window = None
descent_rows_idx = df.index[df["phase"] == "descent"].tolist()
if len(descent_rows_idx) > 20:
    start = descent_rows_idx[len(descent_rows_idx) // 2]
    error_window = set(range(start, start + 5))

packets = []
for idx, r in df.iterrows():
    press = round(pressure_hpa(r.alt_m), 1)
    temp = round(temperature_c(r.alt_m), 1)
    hum = round(humidity_pct(r.alt_m), 1)
    therm = round(thermal_c(r.alt_m), 1)
    status = STATUS_MAP[r.phase]
    if error_window and idx in error_window:
        status = "E"
    cs = checksum(r.lat, r.lon, r.alt_m, press, temp, hum, therm)
    packet = f"TUN,{r.lat:.4f},{r.lon:.4f},{int(r.alt_m)},{press},{temp},{hum},{therm},{cs},{status}"
    packets.append({
        "time_s": r.time_s, "lat": r.lat, "lon": r.lon, "alt_m": r.alt_m,
        "pressure_hpa": press, "temp_c": temp, "humidity_pct": hum,
        "thermal_c": therm, "checksum": cs, "status": status, "packet": packet
    })

tel_df = pd.DataFrame(packets)
tel_df.to_csv("data/sample_flight.csv", index=False)

# ---------------------------------------------------------------
# 6. Config file describing the model (for MockPayload.py in Sprint 1)
# ---------------------------------------------------------------

os.makedirs("payload_simulator/config", exist_ok=True)
flight_profile = {
    "launch_site": {"name": "Kairouan, Tunisia", "lat": LAUNCH_LAT, "lon": LAUNCH_LON, "alt_m": LAUNCH_ALT},
    "burst_altitude_m": BURST_ALTITUDE,
    "ascent_rate_m_s": ASCENT_RATE,
    "descent_model": {"v0_m_s": DESCENT_V0, "scale_height_m": SCALE_HEIGHT},
    "wind_table": [{"alt_m": a, "speed_m_s": s, "heading_deg": h} for a, s, h in WIND_TABLE],
    "sample_interval_s": DT,
    "random_seed": 42,
    "notes": "Simplified hand-authored wind model for software testing only. "
             "NOT a meteorological forecast - do not use for a real launch prediction "
             "(use a tool such as predict.habhub.org / SondeHub's predictor for that)."
}
with open("payload_simulator/config/flight_profile.json", "w") as f:
    json.dump(flight_profile, f, indent=2)

print("Wrote data/flight_path.csv, data/sample_flight.csv, "
      "payload_simulator/config/flight_profile.json")
