"""
app.py
Flask web server for TuniLoon ground station dashboard.
Includes cloud integration (MQTT, Telegram, Sondehub).
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from pathlib import Path

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.Decoder import TelemetryDecoder
from src.Logger import TelemetryLogger

# Import cloud services
from cloud.mqtt_publisher import MQTTPublisher
from cloud.telegram_bot import TelegramBot
from cloud.sondehub_uploader import SondehubUploader

app = Flask(__name__)

# Global data store
telemetry_data = {
    'latest': None,
    'history': [],
    'packet_count': 0,
    'error_count': 0,
    'start_time': datetime.now().isoformat(),
    'cloud_status': {
        'mqtt': 'disconnected',
        'telegram': 'disabled',
        'sondehub': 'disabled'
    }
}

# Initialize components
decoder = TelemetryDecoder()
logger = TelemetryLogger(data_dir="data/", filename="web_dashboard")

# Initialize cloud services
mqtt_publisher = MQTTPublisher()
telegram_bot = TelegramBot()
sondehub = SondehubUploader()

# Configuration
UPDATE_INTERVAL = 1  # seconds
MAX_HISTORY = 1000


@app.route('/')
def index():
    """Render the dashboard."""
    return render_template('index.html')


@app.route('/api/telemetry/latest')
def get_latest():
    """Return the latest telemetry data."""
    return jsonify(telemetry_data['latest'])


@app.route('/api/telemetry/history')
def get_history():
    """Return telemetry history."""
    limit = request.args.get('limit', 100, type=int)
    history = telemetry_data['history'][-limit:]
    return jsonify(history)


@app.route('/api/telemetry/stats')
def get_stats():
    """Return statistics about the telemetry data."""
    stats = {
        'packet_count': telemetry_data['packet_count'],
        'error_count': telemetry_data['error_count'],
        'start_time': telemetry_data['start_time'],
        'history_count': len(telemetry_data['history']),
        'cloud_status': telemetry_data['cloud_status']
    }
    
    if telemetry_data['history']:
        altitudes = [d.get('altitude', 0) for d in telemetry_data['history']]
        stats['max_altitude'] = max(altitudes) if altitudes else 0
        stats['current_altitude'] = altitudes[-1] if altitudes else 0
    
    return jsonify(stats)


@app.route('/api/telemetry/clear')
def clear_data():
    """Clear telemetry history."""
    telemetry_data['history'] = []
    telemetry_data['latest'] = None
    telemetry_data['packet_count'] = 0
    telemetry_data['error_count'] = 0
    return jsonify({'status': 'cleared'})


@app.route('/api/cloud/status')
def cloud_status():
    """Get cloud service status."""
    return jsonify(telemetry_data['cloud_status'])


def process_packet(packet_string: str):
    """Process an incoming telemetry packet."""
    global telemetry_data
    
    data = decoder.decode(packet_string)
    
    if data is None:
        telemetry_data['error_count'] += 1
        return
    
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    
    telemetry_data['latest'] = data
    telemetry_data['packet_count'] += 1
    telemetry_data['history'].append(data)
    
    if len(telemetry_data['history']) > MAX_HISTORY:
        telemetry_data['history'] = telemetry_data['history'][-MAX_HISTORY:]
    
    logger.log(data)
    
    # Publish to MQTT
    try:
        if mqtt_publisher.connected:
            mqtt_publisher.publish(data)
            telemetry_data['cloud_status']['mqtt'] = 'connected'
        else:
            telemetry_data['cloud_status']['mqtt'] = 'disconnected'
    except:
        telemetry_data['cloud_status']['mqtt'] = 'error'
    
    # Send Telegram alerts
    try:
        if telegram_bot.enabled:
            # Check for landing
            if data.get('altitude', 0) < 10 and data.get('status') == 'L':
                telegram_bot.send_landing_alert(data)
            
            # Check for max altitude (peak)
            if data.get('altitude', 0) > 29000:
                telegram_bot.send_max_altitude_alert(data)
            
            telemetry_data['cloud_status']['telegram'] = 'enabled'
    except:
        telemetry_data['cloud_status']['telegram'] = 'error'
    
    # Upload to Sondehub
    try:
        if sondehub.enabled:
            sondehub.upload(data)
            telemetry_data['cloud_status']['sondehub'] = 'enabled'
        else:
            telemetry_data['cloud_status']['sondehub'] = 'disabled'
    except:
        telemetry_data['cloud_status']['sondehub'] = 'error'
    
    # Print to console
    print(f"[DATA] Packet {telemetry_data['packet_count']}: "
          f"Alt={data['altitude']}m, Temp={data['temperature']}°C, "
          f"Status={data['status']}")


def run_mock_consumer():
    """Run the mock payload in continuous mode."""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    from payload_simulator.src.MockPayload import MockPayload
    
    run_mock_consumer.running = True
    packet_interval = 1  # seconds
    
    print("[INFO] Mock consumer started. Sending data to dashboard...")
    
    payload = MockPayload(continuous=True)
    payload.generate_flight()
    
    # Connect MQTT
    mqtt_publisher.connect()
    
    print(f"[INFO] Starting with flight path #{payload.flight_cycle}")
    
    total_sent = 0
    
    while run_mock_consumer.running:
        data = payload.get_next_packet()
        
        if data is None:
            print("[INFO] No more packets, regenerating...")
            payload.generate_flight()
            continue
        
        packet = payload.packer.pack_from_dict(data)
        process_packet(packet)
        total_sent += 1
        
        if total_sent % 10 == 0:
            print(f"[INFO] Sent {total_sent} packets total. "
                  f"Current: Alt={data['altitude']:.0f}m, Status={data['status']}")
        
        time.sleep(packet_interval)


def run_mock_consumer_thread():
    """Start the mock consumer in a background thread."""
    run_mock_consumer.running = True
    thread = threading.Thread(target=run_mock_consumer)
    thread.daemon = True
    thread.start()
    return thread


@app.route('/api/telemetry/mock/start')
def start_mock_data():
    """Start generating mock telemetry data."""
    if hasattr(run_mock_consumer, 'running'):
        run_mock_consumer.running = True
    run_mock_consumer_thread()
    return jsonify({'status': 'started'})


@app.route('/api/telemetry/mock/stop')
def stop_mock_data():
    """Stop generating mock telemetry data."""
    run_mock_consumer.running = False
    return jsonify({'status': 'stopped'})


@app.route('/api/telemetry/debug')
def debug_data():
    """Debug endpoint to check what's in the data store."""
    latest_alt = telemetry_data['latest']['altitude'] if telemetry_data['latest'] else None
    return jsonify({
        'packet_count': telemetry_data['packet_count'],
        'history_length': len(telemetry_data['history']),
        'latest_altitude': latest_alt,
        'error_count': telemetry_data['error_count'],
        'cloud_status': telemetry_data['cloud_status']
    })


if __name__ == '__main__':
    print("=" * 60)
    print("  TuniLoon Ground Station Dashboard")
    print("  http://localhost:5000")
    print("=" * 60)
    print()
    print("[INFO] Starting web server...")
    print("[INFO] Cloud integrations:")
    print(f"  - MQTT: {'enabled' if mqtt_publisher.mqtt_config else 'disabled'}")
    print(f"  - Telegram: {'enabled' if telegram_bot.enabled else 'disabled'}")
    print(f"  - Sondehub: {'enabled' if sondehub.enabled else 'disabled'}")
    print()
    
    # Start mock data generation
    run_mock_consumer_thread()
    
    # Run Flask server
    app.run(debug=True, host='0.0.0.0', port=5000)
