# TuniLoon – Sprint 0.4: Mock Flight Path

## Files delivered

| File | Contents |
|---|---|
| `flight_path.csv` | The core ask: `time_s, lat, lon, alt_m, phase` — one row every 10s |
| `sample_flight.csv` | Same flight, but formatted as full Sprint-0.3 telemetry packets (`TUN,...` string per row), ready to feed `MockPayload.py` in Sprint 1 |
| `flight_profile.json` | Machine-readable model parameters (launch site, ascent rate, wind table, descent model) — save this to `payload_simulator/config/` |

## This run's numbers

- **Launch site:** Kairouan, Tunisia (35.6781, 10.0963) — inland, ~65m ASL
- **Ascent:** 0 → 30,000m in **86.2 min** at a constant 5.8 m/s
- **Burst:** 30,000m
- **Descent:** 30,000m → 0m in **41.2 min** (fast near burst, slowing near the ground as air thickens)
- **Total flight time:** ~127 min (~2h 7min)
- **Landing point:** 35.518°N, 11.038°E — about **87 km** from launch, drifted east/ENE
- **Note:** this run's landing point comes out very close to the eastern coast near Mahdia. That's a real risk profile for inland Tunisian launches when winds carry the balloon toward the Mediterranean — which is exactly the scenario your 4G/SMS backup module (SIM7000E) is designed for. Worth flagging as a real recovery-planning risk, not just a simulator quirk.

## How the model works

- **Ascent:** constant-rate climb (real balloons are close to this if properly filled).
- **Descent:** terminal velocity under parachute grows with altitude because air density drops — modeled as `v(h) = 5 m/s × exp(h / 14000)`, so the balloon falls fast right after burst and slows as it nears the ground. That's why descent is faster (41 min) than the flat 30-45 min guess in the spec — a real parachute descent from 30km is genuinely brisk up top.
- **Wind drift:** a **hand-authored, altitude-banded** wind table (speed + heading), not a live forecast — light easterly winds near the ground, a strong simulated jet-stream band around 9km (35 m/s), then a wind-direction reversal higher up (typical of the stratosphere). Small random turbulence is layered on top so the track isn't perfectly smooth. Horizontal drift is integrated at each altitude the balloon passes through, both on ascent and descent.
- **Telemetry fields** (pressure/temp/humidity/thermal) are generated from standard-atmosphere formulas as a function of altitude, so `sample_flight.csv` already validates against your Sprint 0.3 checksum rule.
- A short GPS-loss window (`status = E`) is injected partway through descent, and `status = F` marks the burst row — both useful for exercising Sprint 2/5 error-handling and validation code.

## Important caveat

This is a **simulator input**, not a flight prediction. The wind table is illustrative, tuned to produce a realistic-looking, moderately complex track for testing your ground station software — it is not derived from real Tunisian atmospheric data. For an actual launch, run a proper prediction (e.g. SondeHub's predictor) closer to launch day.

## Reproducibility

`random_seed = 42` in `flight_profile.json` — rerunning `generate_flight_path.py` gives you the identical track. Change the seed (or the wind table) to get different mock flights for testing edge cases.
