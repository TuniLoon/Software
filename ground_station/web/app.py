"""
app.py
TuniLoon Ground Station – Full Version with Config
"""

import sys
import traceback
import math
from pathlib import Path
from datetime import datetime, timedelta

# Load config first
from ground_station.src.config import config
sys.path.insert(0, str(config.BASE_DIR))

import time
import threading
from flask import Flask, render_template, jsonify, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, ValidationError

from ground_station.src.Decoder import TelemetryDecoder
from ground_station.src.Logger import TelemetryLogger
from ground_station.src.database import Database
from ground_station.src.logger_config import setup_logging, get_logger
from cloud.mqtt_publisher import MQTTPublisher
from cloud.telegram_bot import TelegramBot
from cloud.sondehub_uploader import SondehubUploader
from ground_station.src.weather_service import WeatherService
from ml.real_time_detector import RealTimeAnomalyDetector

# Setup logging
setup_logging(
    level=config.LOG_LEVEL,
    log_file=str(config.LOG_FILE),
    max_bytes=config.LOG_MAX_BYTES,
    backup_count=config.LOG_BACKUP_COUNT
)
logger = get_logger(__name__)

app = Flask(__name__)

# ------------------------- Rate Limiter -------------------------
limiter = Limiter(app)
limiter.default_limits = [config.RATE_LIMIT_DEFAULT]

# ------------------------- Input Validation Schemas -------------------------
class PlannerSchema(Schema):
    lat = fields.Float(required=True, validate=lambda x: -90 <= x <= 90)
    lon = fields.Float(required=True, validate=lambda x: -180 <= x <= 180)
    launch_time = fields.Str(required=True)

class TrajectorySchema(Schema):
    lat = fields.Float(validate=lambda x: -90 <= x <= 90)
    lon = fields.Float(validate=lambda x: -180 <= x <= 180)
    duration = fields.Int(load_default=3600)

class TelemetryProcessSchema(Schema):
    packet = fields.Str(required=True)

# ------------------------- Global Variables -------------------------
simulation_real_time = config.REAL_TIME_MODE
packet_counter = 0

# ------------------------- Component Initialization -------------------------
decoder = TelemetryDecoder()
logger_telemetry = TelemetryLogger(data_dir=str(config.DATA_DIR), filename="web_dashboard")
db = Database(db_path=str(config.DB_PATH))
mqtt_publisher = MQTTPublisher()
telegram_bot = TelegramBot()
sondehub = SondehubUploader()
weather_service = WeatherService()

anomaly_detector = RealTimeAnomalyDetector()
model_path = config.ANOMALY_MODEL_PATH
if model_path.exists():
    try:
        anomaly_detector.detector.load_model(str(model_path))
        anomaly_detector.is_initialized = True
        logger.info("Loaded trained model from disk")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        anomaly_detector.initialize()
else:
    anomaly_detector.initialize()
    logger.info("No trained model found; using random initialization")

current_flight_id = db.create_flight()
logger.info(f"New flight session created: ID {current_flight_id}")

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
        logger.error(f"Error in /api/telemetry/latest: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/history')
@limiter.limit("30 per minute")
def get_history():
    try:
        limit = request.args.get('limit', 100, type=int)
        return jsonify(get_history_from_db(limit))
    except Exception as e:
        logger.error(f"Error in /api/telemetry/history: {e}")
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
        logger.error(f"Error in /api/telemetry/stats: {e}")
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

# ------------------------- Analysis Routes (Sprint 8) -------------------------
@app.route('/analysis')
def analysis_page():
    return render_template('analysis.html')

@app.route('/api/analysis/latest')
@limiter.limit("10 per minute")
def analysis_latest():
    if not get_history_from_db(1):
        return jsonify({'error': 'No flight data available'}), 404
    from analysis.flight_analyzer import FlightAnalyzer
    from analysis.wind_estimator import WindEstimator
    from analysis.report_generator import ReportGenerator
    data = get_history_from_db(1000)
    analyzer = FlightAnalyzer(data)
    metrics = analyzer.get_metrics()
    wind = WindEstimator(data)
    wind_speed, wind_direction = wind.get_wind()
    report_gen = ReportGenerator(metrics, wind_speed, wind_direction)
    report_md = report_gen.generate_markdown()
    return jsonify({
        'metrics': metrics,
        'wind_speed': wind_speed,
        'wind_direction': wind_direction,
        'report_markdown': report_md
    })

@app.route('/api/analysis/report/download')
@limiter.limit("5 per minute")
def analysis_report_download():
    if not get_history_from_db(1):
        return jsonify({'error': 'No flight data'}), 404
    from analysis.flight_analyzer import FlightAnalyzer
    from analysis.wind_estimator import WindEstimator
    from analysis.report_generator import ReportGenerator
    data = get_history_from_db(1000)
    analyzer = FlightAnalyzer(data)
    metrics = analyzer.get_metrics()
    wind = WindEstimator(data)
    wind_speed, wind_direction = wind.get_wind()
    report_gen = ReportGenerator(metrics, wind_speed, wind_direction)
    filename = report_gen.save_markdown()
    return send_file(filename, as_attachment=True)

# ------------------------- Multi-Balloon (Sprint 9) -------------------------
@app.route('/multi')
def multi_balloon():
    return render_template('multi_index.html')

# ------------------------- Flight Planner (Sprint 11) -------------------------
@app.route('/planner')
def planner():
    return render_template('planner.html')

@app.route('/api/planner/predict', methods=['POST'])
@limiter.limit("5 per minute")
def planner_predict():
    try:
        schema = PlannerSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Invalid input', 'details': err.messages}), 400
    from analysis.flight_planner import FlightPlanner
    lat = data['lat']
    lon = data['lon']
    try:
        launch_time = datetime.fromisoformat(data['launch_time'])
    except ValueError:
        return jsonify({'error': 'Invalid datetime format'}), 400
    planner = FlightPlanner(weather_service)
    result = planner.predict_landing(lat, lon, launch_time)
    return jsonify(result)

# ------------------------- Export Routes (Sprint 12) -------------------------
@app.route('/api/export/kml')
@limiter.limit("5 per minute")
def export_kml():
    if not get_history_from_db(1):
        return jsonify({'error': 'No flight data'}), 404
    from analysis.export_handlers import to_kml
    traj = telemetry_data['history']
    kml = to_kml(traj)
    return app.response_class(kml, mimetype='application/vnd.google-earth.kml+xml',
                              headers={'Content-Disposition': 'attachment;filename=flight.kml'})

@app.route('/api/export/gpx')
@limiter.limit("5 per minute")
def export_gpx():
    if not get_history_from_db(1):
        return jsonify({'error': 'No flight data'}), 404
    from analysis.export_handlers import to_gpx
    traj = telemetry_data['history']
    gpx = to_gpx(traj)
    return app.response_class(gpx, mimetype='application/gpx+xml',
                              headers={'Content-Disposition': 'attachment;filename=flight.gpx'})

@app.route('/api/sim/toggle', methods=['POST'])
@limiter.limit("10 per minute")
def toggle_simulation_speed():
    global simulation_real_time
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'Invalid JSON'}), 400
    real_time = data.get('real_time', False)
    simulation_real_time = real_time
    logger.info(f"Simulation mode set to {'real-time' if real_time else 'fast'}")
    return jsonify({'status': 'ok', 'real_time': real_time})

# ------------------------- Weather Routes (Sprint 10) -------------------------
@app.route('/api/weather/current')
@limiter.limit("10 per minute")
def weather_current():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return jsonify({'error': 'Missing lat/lon'}), 400
    data = weather_service.get_current_weather(lat, lon)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Weather data unavailable'}), 500

@app.route('/api/weather/forecast')
@limiter.limit("10 per minute")
def weather_forecast():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    cnt = request.args.get('cnt', 8, type=int)
    if lat is None or lon is None:
        return jsonify({'error': 'Missing lat/lon'}), 400
    data = weather_service.get_forecast(lat, lon, cnt)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Forecast unavailable'}), 500

@app.route('/api/weather/wind')
@limiter.limit("10 per minute")
def weather_wind():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return jsonify({'error': 'Missing lat/lon'}), 400
    wind = weather_service.get_wind(lat, lon)
    if wind:
        return jsonify(wind)
    return jsonify({'error': 'Wind data unavailable'}), 500

# ------------------------- History Routes (Sprint 13) -------------------------
@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/api/history/list')
@limiter.limit("10 per minute")
def history_list():
    from analysis.historical_browser import HistoricalBrowser
    browser = HistoricalBrowser(data_dir=str(config.DATA_DIR))
    flights = browser.list_flights()
    return jsonify(flights)

@app.route('/api/history/report/<flight_id>')
@limiter.limit("5 per minute")
def history_report(flight_id):
    from analysis.historical_browser import HistoricalBrowser
    from analysis.pdf_report_generator import PDFReportGenerator
    browser = HistoricalBrowser(data_dir=str(config.DATA_DIR))
    data = browser.get_flight_data(flight_id)
    if not data:
        return jsonify({'error': 'Flight not found'}), 404
    generator = PDFReportGenerator(data)
    pdf_bytes = generator.generate()
    return app.response_class(pdf_bytes, mimetype='application/pdf',
                              headers={'Content-Disposition': f'attachment;filename=report_{flight_id}.pdf'})

# ------------------------- Wind & Trajectory (Sprint 14) -------------------------
@app.route('/wind')
def wind_page():
    return render_template('wind.html')

@app.route('/api/wind/current')
@limiter.limit("10 per minute")
def wind_current():
    if len(get_history_from_db(20)) < 2:
        return jsonify({'error': 'Not enough data'}), 400
    from analysis.wind_estimator import WindEstimator
    data = get_history_from_db(1000)[-20:]
    estimator = WindEstimator(data)
    wind = estimator.get_wind_with_confidence()
    latest = get_latest_from_db()
    if latest:
        wind['latitude'] = latest.get('latitude')
        wind['longitude'] = latest.get('longitude')
    return jsonify(wind)

@app.route('/api/predict/trajectory', methods=['POST'])
@limiter.limit("5 per minute")
def predict_trajectory():
    try:
        schema = TrajectorySchema()
        req_data = schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({'error': 'Invalid input', 'details': err.messages}), 400

    lat = req_data.get('lat')
    lon = req_data.get('lon')
    if lat is None or lon is None:
        latest = get_latest_from_db()
        if latest:
            lat = latest.get('latitude', 35.8276)
            lon = latest.get('longitude', 10.6402)
        else:
            lat, lon = 35.8276, 10.6402

    wind_resp = wind_current()
    if wind_resp.status_code != 200:
        wind_speed = 8.0
        wind_dir = 135
    else:
        wind_data = wind_resp.get_json()
        wind_speed = wind_data.get('speed', 8.0)
        wind_dir = wind_data.get('direction', 135)

    duration = req_data.get('duration', 3600)
    step = 60
    points = []
    cur_lat, cur_lon = lat, lon
    total_time = 0

    while total_time < duration:
        dir_rad = math.radians(wind_dir)
        dx = wind_speed * step * math.sin(dir_rad)
        dy = wind_speed * step * math.cos(dir_rad)
        lat_change = dy / 111320
        lon_change = dx / (111320 * math.cos(math.radians(cur_lat)))
        cur_lat += lat_change
        cur_lon += lon_change
        total_time += step

        if total_time < 3000:
            alt = min(5 * total_time, 30000)
        else:
            alt = max(30000 - 15 * (total_time - 3000), 0)

        points.append({
            'time': total_time,
            'latitude': cur_lat,
            'longitude': cur_lon,
            'altitude': alt
        })
        if alt <= 0 and total_time > 600:
            break

    if not points:
        return jsonify({'error': 'Prediction failed'}), 500

    last = points[-1]
    return jsonify({
        'landing_lat': last['latitude'],
        'landing_lon': last['longitude'],
        'landing_time': (datetime.now() + timedelta(seconds=last['time'])).isoformat(),
        'duration': last['time'],
        'trajectory': points
    })

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
            confidence_threshold = config.ANOMALY_CONFIDENCE_THRESHOLD
            is_anomaly = anomaly_result['is_anomaly'] and anomaly_result['confidence'] > confidence_threshold
            data['anomaly'] = bool(is_anomaly)
            data['anomaly_score'] = float(anomaly_result['anomaly_score'])
            data['anomaly_confidence'] = float(anomaly_result['confidence'])
            if anomaly_result['alert_triggered']:
                logger.info(f"ANOMALY detected in packet {packet_counter}")
                if telegram_bot.enabled:
                    telegram_bot.send_message(
                        f"🚨 <b>Anomaly Detected!</b>\n\n"
                        f"Alt: {data['altitude']:.0f}m, Temp: {data['temperature']:.1f}°C\n"
                        f"Score: {data['anomaly_score']:.2f}, Confidence: {data['anomaly_confidence']:.2f}"
                    )
        else:
            data['anomaly'] = False
            data['anomaly_score'] = 0.0
            data['anomaly_confidence'] = 0.0

        db.insert_telemetry(current_flight_id, data)
        logger_telemetry.log(data)
        logger.info(f"Packet {packet_counter}: Alt={data['altitude']}m, Status={data['status']}")

    except Exception as e:
        logger.error(f"Error processing packet: {e}\n{traceback.format_exc()}")

# ------------------------- Mock Consumer -------------------------
def run_mock_consumer():
    global simulation_real_time
    import sys
    from pathlib import Path
    sys.path.append(str(config.BASE_DIR))
    from payload_simulator.src.MockPayload import MockPayload

    run_mock_consumer.running = True
    packet_interval = config.SIMULATION_INTERVAL
    logger.info("Mock consumer started.")
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
            logger.error(f"Mock consumer error: {e}\n{traceback.format_exc()}")
            time.sleep(1)

def run_mock_consumer_thread():
    run_mock_consumer.running = True
    thread = threading.Thread(target=run_mock_consumer)
    thread.daemon = True
    thread.start()
    return thread

# ------------------------- Entry Point -------------------------
if __name__ == '__main__':
    logger.info("Starting TuniLoon Ground Station")
    logger.info(f"http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    logger.info(f"Telegram enabled: {telegram_bot.enabled}")
    run_mock_consumer_thread()
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
