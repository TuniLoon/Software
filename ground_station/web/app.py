"""
app.py
TuniLoon Ground Station – SQLite + Polling (No WebSockets)
"""

import sys
import traceback
import math
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import threading
from flask import Flask, render_template, jsonify, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, ValidationError

from ground_station.src.Decoder import TelemetryDecoder
from ground_station.src.Logger import TelemetryLogger
from ground_station.src.database import Database
from cloud.mqtt_publisher import MQTTPublisher
from cloud.telegram_bot import TelegramBot
from cloud.sondehub_uploader import SondehubUploader
from ground_station.src.weather_service import WeatherService
from ml.real_time_detector import RealTimeAnomalyDetector

app = Flask(__name__)

# ------------------------- Rate Limiter -------------------------
limiter = Limiter(app)
limiter.default_limits = ["200 per day", "50 per hour"]

# ------------------------- Input Validation Schemas -------------------------
class PlannerSchema(Schema):
    lat = fields.Float(required=True, validate=lambda x: -90 <= x <= 90)
    lon = fields.Float(required=True, validate=lambda x: -180 <= x <= 180)
    launch_time = fields.Str(required=True)

class TrajectorySchema(Schema):
    lat = fields.Float(validate=lambda x: -90 <= x <= 90)
    lon = fields.Float(validate=lambda x: -180 <= x <= 180)
    duration = fields.Int(load_default=3600)

# ------------------------- Global Variables -------------------------
simulation_real_time = False
packet_counter = 0

# ------------------------- Component Initialization -------------------------
decoder = TelemetryDecoder()
logger = TelemetryLogger(data_dir="data/", filename="web_dashboard")
db = Database()
mqtt_publisher = MQTTPublisher()
telegram_bot = TelegramBot()
sondehub = SondehubUploader()
weather_service = WeatherService()

anomaly_detector = RealTimeAnomalyDetector()
model_path = Path(__file__).parent.parent.parent / "ml/models/anomaly_model.pkl"
if model_path.exists():
    try:
        anomaly_detector.detector.load_model(str(model_path))
        anomaly_detector.is_initialized = True
        print("[ML] Loaded trained model from disk")
    except Exception as e:
        print(f"[ML] Failed to load model: {e}")
        anomaly_detector.initialize()
else:
    anomaly_detector.initialize()
    print("[ML] No trained model found; using random initialization")

current_flight_id = db.create_flight()
print(f"[DB] New flight session created: ID {current_flight_id}")

MAX_HISTORY = 1000

# ------------------------- Helper Functions -------------------------
def get_latest_from_db():
    return db.get_latest(current_flight_id)

def get_history_from_db(limit=100):
    return db.get_history(current_flight_id, limit)

# ------------------------- Main Routes -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/telemetry/latest')
@limiter.limit("30 per minute")
def get_latest():
    try:
        return jsonify(get_latest_from_db())
    except Exception as e:
        app.logger.error(f"Error in /api/telemetry/latest: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/history')
@limiter.limit("30 per minute")
def get_history():
    try:
        limit = request.args.get('limit', 100, type=int)
        return jsonify(get_history_from_db(limit))
    except Exception as e:
        app.logger.error(f"Error in /api/telemetry/history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/stats')
@limiter.limit("30 per minute")
def get_stats():
    try:
        flights = db.get_flights()
        if not flights:
            return jsonify({
                'packet_count': 0,
                'error_count': 0,
                'start_time': datetime.now().isoformat(),
                'history_count': 0,
                'cloud_status': {'mqtt': 'disconnected', 'telegram': 'disabled', 'sondehub': 'disabled'},
                'max_altitude': 0,
                'current_altitude': 0
            })
        latest_flight = flights[0]
        history = get_history_from_db(100)
        altitudes = [d.get('altitude', 0) for d in history]
        return jsonify({
            'packet_count': latest_flight.get('packet_count', 0),
            'error_count': 0,
            'start_time': latest_flight.get('start_time', datetime.now().isoformat()),
            'history_count': len(history),
            'cloud_status': {
                'mqtt': 'connected' if mqtt_publisher.connected else 'disconnected',
                'telegram': 'enabled' if telegram_bot.enabled else 'disabled',
                'sondehub': 'enabled' if sondehub.enabled else 'disabled'
            },
            'max_altitude': latest_flight.get('max_altitude', 0),
            'current_altitude': altitudes[-1] if altitudes else 0
        })
    except Exception as e:
        app.logger.error(f"Error in /api/telemetry/stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/clear')
def clear_data():
    db.clear_all()
    global current_flight_id
    current_flight_id = db.create_flight()
    telegram_bot.reset_state()
    anomaly_detector.reset()
    return jsonify({'status': 'cleared'})

@app.route('/api/cloud/status')
def cloud_status():
    return jsonify({
        'mqtt': 'connected' if mqtt_publisher.connected else 'disconnected',
        'telegram': 'enabled' if telegram_bot.enabled else 'disabled',
        'sondehub': 'enabled' if sondehub.enabled else 'disabled'
    })

@app.route('/api/debug')
def debug():
    flights = db.get_flights()
    latest = get_latest_from_db()
    return jsonify({
        'flights': flights[:5],
        'latest': latest,
        'current_flight_id': current_flight_id
    })

# ------------------------- Test & Process Endpoints -------------------------
@app.route('/api/test')
def test():
    return jsonify({'status': 'ok'})

@app.route('/api/telemetry/process', methods=['POST'])
def process_telemetry_endpoint():
    data = request.get_json()
    if not data or 'packet' not in data:
        return jsonify({'error': 'Missing packet'}), 400
    process_packet(data['packet'])
    return jsonify({'status': 'ok'})

# ------------------------- Other Routes (Analysis, Planner, Export, History, Wind) -------------------------
@app.route('/analysis')
def analysis_page():
    return render_template('analysis.html')

@app.route('/multi')
def multi_balloon():
    return render_template('multi_index.html')

@app.route('/planner')
def planner():
    return render_template('planner.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/wind')
def wind_page():
    return render_template('wind.html')

# ... (all other routes remain unchanged) ...

# ------------------------- Payload Processing -------------------------
def process_packet(packet_string: str):
    global current_flight_id, packet_counter
    try:
        data = decoder.decode(packet_string)
        if data is None:
            return
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        packet_counter += 1

        if anomaly_detector.is_initialized:
            anomaly_result = anomaly_detector.process_telemetry(data)
            confidence_threshold = 0.7
            is_anomaly = anomaly_result['is_anomaly'] and anomaly_result['confidence'] > confidence_threshold
            data['anomaly'] = bool(is_anomaly)
            data['anomaly_score'] = float(anomaly_result['anomaly_score'])
            data['anomaly_confidence'] = float(anomaly_result['confidence'])
            if anomaly_result['alert_triggered']:
                print(f"🚨 ANOMALY detected in packet {packet_counter}")
                if telegram_bot.enabled:
                    telegram_bot.send_message(...)
        else:
            data['anomaly'] = False
            data['anomaly_score'] = 0.0
            data['anomaly_confidence'] = 0.0

        db.insert_telemetry(current_flight_id, data)
        logger.log(data)
        print(f"[DATA] Packet {packet_counter}: Alt={data['altitude']}m, Status={data['status']}")

    except Exception as e:
        app.logger.error(f"Error processing packet: {e}\n{traceback.format_exc()}")

# ------------------------- Mock Consumer -------------------------
def run_mock_consumer():
    global simulation_real_time
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from payload_simulator.src.MockPayload import MockPayload

    run_mock_consumer.running = True
    packet_interval = 1
    print("[INFO] Mock consumer started.")
    payload = MockPayload(continuous=True)
    payload.generate_flight()
    mqtt_publisher.connect()

    while run_mock_consumer.running:
        try:
            data = payload.get_next_packet()
            if data is None:
                payload.generate_flight()
                telegram_bot.reset_state()
                anomaly_detector.reset()
                continue
            packet = payload.packer.pack_from_dict(data)
            process_packet(packet)
            if simulation_real_time:
                time.sleep(30)
            else:
                time.sleep(packet_interval)
        except Exception as e:
            app.logger.error(f"Mock consumer error: {e}\n{traceback.format_exc()}")
            time.sleep(1)

def run_mock_consumer_thread():
    run_mock_consumer.running = True
    thread = threading.Thread(target=run_mock_consumer)
    thread.daemon = True
    thread.start()
    return thread

# ------------------------- Entry Point -------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  TuniLoon Ground Station – SQLite + Polling")
    print("  http://localhost:5000")
    print("=" * 60)
    print()
    print("[INFO] Cloud integrations:")
    print(f"  - Telegram: {'enabled' if telegram_bot.enabled else 'disabled'}")
    print()
    run_mock_consumer_thread()
    app.run(host='0.0.0.0', port=5000, debug=False)
