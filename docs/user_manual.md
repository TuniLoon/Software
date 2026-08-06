# TuniLoon User Manual

## Overview

TuniLoon is a high-altitude balloon monitoring system designed for agriculture, healthcare, and disaster management in Tunisia. This manual covers the **ground station software** used to receive, visualize, and analyze telemetry data.

---

## System Requirements

### Hardware
- **Computer:** Laptop or desktop with 4GB+ RAM
- **Network:** Internet connection for cloud services
- **Optional:** LoRa radio module for real hardware

### Software
- **Python:** 3.10 or higher
- **Operating System:** Linux, Windows, or macOS
- **Browser:** Chrome, Firefox, or Edge

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tuniloon-software.git
cd tuniloon-software
```

### 2. Create Conda Environment

```bash
conda create -n tuniloon python=3.10 -y
conda activate tuniloon
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c 'import serial, flask, folium, pandas, numpy, plotly, paho_mqtt; print("✅ All libraries installed!")'
```

---

## Quick Start

### 1. Launch the Dashboard

```bash
python3 ground_station/web/app.py
```

### 2. Open Browser

Navigate to: **http://localhost:5000**

### 3. Start the Mock Payload

The dashboard will automatically start generating mock telemetry data. You should see:
- A map with a moving balloon marker
- Real-time statistics updating
- Graphs populating with data

---

## Using the Dashboard

### Map View
- **Balloon Marker:** Shows current position (orange circle)
- **Path Line:** Displays the flight path (orange line)
- **Coordinates:** Displayed at the top of the map
- **Zoom Controls:** Use mouse wheel or zoom buttons

### Statistics Bar
| Field | Description |
| :--- | :--- |
| **Altitude** | Current altitude in meters |
| **Latitude** | Current latitude (degrees) |
| **Longitude** | Current longitude (degrees) |
| **Temperature** | Current temperature at the payload (°C) |
| **Pressure** | Atmospheric pressure (hPa) |
| **Status** | Flight phase (Ascent/Descent/Landing) |

### Telemetry Details Panel
Displays detailed telemetry data including:
- Timestamp
- Altitude, Latitude, Longitude
- Temperature, Pressure, Humidity
- Thermal Average (from MLX90640)
- Status and Checksum

### Graphs
- **Altitude Profile:** Shows altitude changes over time with a blue line
- **Temperature Profile:** Shows temperature changes over time with an orange line

### Controls
| Control | Description |
| :--- | :--- |
| **Theme Toggle** | Switch between light and dark mode (moon/sun icon) |
| **Clear Button** | Reset all data and start fresh (trash icon) |
| **Refresh** | Browser refresh to restart if needed |

---

## Cloud Services

### MQTT Configuration

The system automatically publishes telemetry to a public MQTT broker.

**Default Settings:**
- **Broker:** broker.hivemq.com
- **Port:** 1883
- **Topic:** tuniloon/telemetry

**To view data with MQTT Explorer:**
1. Download MQTT Explorer from https://mqtt-explorer.com/
2. Create a new connection:
   - Name: TuniLoon
   - Host: broker.hivemq.com
   - Port: 1883
3. Subscribe to topic: `tuniloon/telemetry`

### Telegram Alerts

Configure `config/cloud_config.json`:

```json
{
    "telegram": {
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "chat_id": "YOUR_CHAT_ID_HERE",
        "enabled": true
    }
}
```

**To get a bot token:**
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the bot token

**To get your chat ID:**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` in the response

**Alerts you'll receive:**
- 📡 "TuniLoon at 5,000m" – Every 5,000m during ascent
- 🎈 "TuniLoon at Peak: 30,000m" – At maximum altitude
- 🔄 "Status Changed: Ascent → Descent" – When descent begins

### Sondehub Integration (Optional)

Configure `config/cloud_config.json`:

```json
{
    "sondehub": {
        "enabled": true,
        "callsign": "TUNILOON",
        "upload_url": "https://api.sondehub.org/v1/telemetry"
    }
}
```

When enabled, telemetry will be visible on https://sondehub.org/

---

## Testing

### Run Flight Simulation

```bash
python3 tests/FlightSimulator.py --interval 2 --verbose
```

### Run Unit Tests

```bash
python3 tests/test_decoder.py
python3 tests/test_logger.py
python3 tests/test_integration.py
```

### Run All Unit Tests

```bash
python3 -m pytest tests/
```

### Run Stress Test (1 hour)

```bash
python3 tests/stress_test.py --hours 1 --interval 30
```

### Generate Flight Report

```bash
python3 tests/FlightReport.py data/flight_simulation.csv
```

---

## Project Structure

```
tuniloon-software/
├── payload_simulator/          # Mock payload generator
│   └── src/
│       ├── FlightPathGenerator.py
│       ├── SensorSimulator.py
│       ├── TelemetryPacker.py
│       └── MockPayload.py
├── ground_station/             # Ground station software
│   └── src/
│       ├── Config.py
│       ├── Decoder.py
│       ├── Logger.py
│       └── Receiver.py
│   └── web/
│       ├── app.py
│       ├── templates/
│       │   └── index.html
│       └── static/
│           ├── style.css
│           └── dashboard.js
├── cloud/                      # Cloud integrations
│   ├── mqtt_publisher.py
│   ├── telegram_bot.py
│   └── sondehub_uploader.py
├── tests/                      # Tests and simulations
│   ├── FlightSimulator.py
│   ├── test_decoder.py
│   ├── test_logger.py
│   ├── test_integration.py
│   ├── stress_test.py
│   └── FlightReport.py
├── config/
│   ├── settings.json
│   └── cloud_config.json
├── docs/
│   ├── telemetry_protocol.md
│   ├── user_manual.md
│   └── architecture.md
├── scripts/
│   └── run_simulation.sh
├── data/                       # Logged flight data
├── requirements.txt
└── README.md
```

---

## Telemetry Protocol

### Packet Format

```
TUN,<lat>,<lon>,<alt>,<press>,<temp>,<hum>,<thermal>,<checksum>,<status>
```

### Example Packet

```
TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,A
```

### Status Codes

| Code | Meaning |
| :--- | :--- |
| `A` | Ascent (climbing) |
| `D` | Descent (falling) |
| `L` | Landing (on ground) |
| `E` | Error (sensor failure) |
| `F` | Cut-down (emergency) |

For full details, see: `docs/telemetry_protocol.md`

---

## Troubleshooting

### Dashboard Won't Load

| Issue | Solution |
| :--- | :--- |
| Flask not installed | `pip install flask` |
| Port 5000 in use | Change port in `app.py` (last line) |
| Module not found | `pip install -r requirements.txt` |

### No Data Appearing

| Issue | Solution |
| :--- | :--- |
| MockPayload not running | Check terminal for errors |
| Wrong interval | Use `--interval 1` for faster testing |
| Browser cache | Refresh with Ctrl+Shift+R |

### MQTT Not Connecting

| Issue | Solution |
| :--- | :--- |
| No internet | Check network connection |
| Wrong broker | Verify `broker.hivemq.com` |
| Firewall | Allow outbound port 1883 |

### Telegram Alerts Not Working

| Issue | Solution |
| :--- | :--- |
| Bot token invalid | Regenerate with BotFather |
| Chat ID wrong | Check `/getUpdates` response |
| Disabled in config | Set `"enabled": true` |

### Graphs Not Updating

| Issue | Solution |
| :--- | :--- |
| Plotly not loaded | Check browser console for errors |
| Data not reaching frontend | Check `/api/telemetry/debug` endpoint |
| Browser cache | Hard refresh (Ctrl+Shift+R) |

---

## File Locations

| File | Location | Purpose |
| :--- | :--- | :--- |
| Dashboard | `ground_station/web/app.py` | Web server |
| Decoder | `ground_station/src/Decoder.py` | Packet validation |
| Logger | `ground_station/src/Logger.py` | Data logging |
| Mock Payload | `payload_simulator/src/MockPayload.py` | Simulation |
| Config | `config/settings.json` | Project settings |
| Cloud Config | `config/cloud_config.json` | Cloud credentials |
| Test Reports | `data/flight_report_*.txt` | Generated reports |

---

## Support

### Contact
- **Team Lead:** Saif Maammar
- **SCRUM Master:** Amal Karaoud
- **Payload Lead:** Mahdi BenSlima
- **Ground Station Lead:** Nesrine Zouari

### Resources
- **GitHub:** https://github.com/yourusername/tuniloon-software
- **Documentation:** `docs/` folder
- **Telemetry Protocol:** `docs/telemetry_protocol.md`
- **Architecture:** `docs/architecture.md`

### Reporting Issues
Please create a GitHub issue with:
1. Description of the problem
2. Steps to reproduce
3. Expected vs actual behavior
4. Screenshots or logs (if applicable)

---

## License

This project is licensed under the MIT License – see the LICENSE file for details.

---

**Made with ❤️ by the TuniLoon Team 🇹🇳**
