"""
app.py
TuniLoon Ground Station – Full Integration (All Sprints) + Security (Sprint 15)
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

class TelemetryProcessSchema(Schema):
    packet = fields.Str(required=True)

# ------------------------- Global Variables -------------------------
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

simulation_real_time = False

# ------------------------- Component Initialization -------------------------
decoder = TelemetryDecoder()
logger = TelemetryLogger(data_dir="data/", filename="web_dashboard")
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

MAX_HISTORY = 1000

# ------------------------- Main Routes -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/telemetry/latest')
@limiter.limit("30 per minute")
def get_latest():
    try:
        return jsonify(telemetry_data['latest'])
    except Exception as e:
        app.logger.error(f"Error in /api/telemetry/latest: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/history')
@limiter.limit("30 per minute")
def get_history():
    try:
        limit = request.args.get('limit', 100, type=int)
        return jsonify(telemetry_data['history'][-limit:])
    except Exception as e:
        app.logger.error(f"Error in /api/telemetry/history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/stats')
@limiter.limit("30 per minute")
def get_stats():
    try:
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
    except Exception as e:
        app.logger.error(f"Error in /api/telemetry/stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry/clear')
def clear_data():
    telemetry_data['history'] = []
    telemetry_data['latest'] = None
    telemetry_data['packet_count'] = 0
    telemetry_data['error_count'] = 0
    telegram_bot.reset_state()
    anomaly_detector.reset()
    return jsonify({'status': 'cleared'})

@app.route('/api/cloud/status')
def cloud_status():
    return jsonify(telemetry_data['cloud_status'])

@app.route('/api/debug')
def debug():
    return jsonify({
        'packet_count': telemetry_data['packet_count'],
        'history_len': len(telemetry_data['history']),
        'latest': telemetry_data['latest'],
        'error_count': telemetry_data['error_count']
    })

# ------------------------- Analysis Routes (Sprint 8) -------------------------
@app.route('/analysis')
def analysis_page():
    return render_template('analysis.html')

@app.route('/api/analysis/latest')
@limiter.limit("10 per minute")
def analysis_latest():
    if not telemetry_data['history']:
        return jsonify({'error': 'No flight data available'}), 404
    from analysis.flight_analyzer import FlightAnalyzer
    from analysis.wind_estimator import WindEstimator
    from analysis.report_generator import ReportGenerator
    data = telemetry_data['history']
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
    if not telemetry_data['history']:
        return jsonify({'error': 'No flight data'}), 404
    from analysis.flight_analyzer import FlightAnalyzer
    from analysis.wind_estimator import WindEstimator
    from analysis.report_generator import ReportGenerator
    data = telemetry_data['history']
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
    if not telemetry_data['history']:
        return jsonify({'error': 'No flight data'}), 404
    from analysis.export_handlers import to_kml
    traj = telemetry_data['history']
    kml = to_kml(traj)
    return app.response_class(kml, mimetype='application/vnd.google-earth.kml+xml',
                              headers={'Content-Disposition': 'attachment;filename=flight.kml'})

@app.route('/api/export/gpx')
@limiter.limit("5 per minute")
def export_gpx():
    if not telemetry_data['history']:
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
    print(f"[INFO] Simulation mode set to {'real-time' if real_time else 'fast'}")
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
    browser = HistoricalBrowser()
    flights = browser.list_flights()
    return jsonify(flights)

@app.route('/api/history/report/<flight_id>')
@limiter.limit("5 per minute")
def history_report(flight_id):
    from analysis.historical_browser import HistoricalBrowser
    from analysis.pdf_report_generator import PDFReportGenerator
    browser = HistoricalBrowser()
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
    if not telemetry_data['history'] or len(telemetry_data['history']) < 2:
        return jsonify({'error': 'Not enough data'}), 400
    from analysis.wind_estimator import WindEstimator
    data = telemetry_data['history'][-20:]
    estimator = WindEstimator(data)
    wind = estimator.get_wind_with_confidence()
    latest = telemetry_data['latest']
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
        latest = telemetry_data.get('latest')
        if latest:
            lat = latest.get('latitude', 35.8276)
            lon = latest.get('longitude', 10.6402)
        else:
            lat, lon = 35.8276, 10.6402

    # Get wind estimate
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
    global telemetry_data
    try:
        data = decoder.decode(packet_string)
        if data is None:
            telemetry_data['error_count'] += 1
            return
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        if anomaly_detector.is_initialized:
            anomaly_result = anomaly_detector.process_telemetry(data)
            confidence_threshold = 0.7
            is_anomaly = anomaly_result['is_anomaly'] and anomaly_result['confidence'] > confidence_threshold
            data['anomaly'] = bool(is_anomaly)
            data['anomaly_score'] = float(anomaly_result['anomaly_score'])
            data['anomaly_confidence'] = float(anomaly_result['confidence'])
            if anomaly_result['alert_triggered']:
                print(f"🚨 ANOMALY detected in packet {telemetry_data['packet_count']}")
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
        
        telemetry_data['latest'] = data
        telemetry_data['packet_count'] += 1
        telemetry_data['history'].append(data)
        if len(telemetry_data['history']) > MAX_HISTORY:
            telemetry_data['history'] = telemetry_data['history'][-MAX_HISTORY:]
        
        logger.log(data)
        
        # MQTT
        try:
            if mqtt_publisher.connected:
                mqtt_publisher.publish(data)
                telemetry_data['cloud_status']['mqtt'] = 'connected'
        except Exception as e:
            app.logger.error(f"MQTT error: {e}")
            telemetry_data['cloud_status']['mqtt'] = 'error'
        
        # Telegram status
        try:
            if telegram_bot.enabled:
                if telemetry_data['packet_count'] % 50 == 0:
                    telegram_bot.send_message(
                        f"📡 <b>TuniLoon Update</b>\n\n"
                        f"Alt: {data['altitude']:.0f}m\n"
                        f"Status: {data.get('status_description', 'Unknown')}\n"
                        f"Temp: {data['temperature']:.1f}°C"
                    )
                telemetry_data['cloud_status']['telegram'] = 'enabled'
        except Exception as e:
            app.logger.error(f"Telegram error: {e}")
            telemetry_data['cloud_status']['telegram'] = 'error'
        
        # Sondehub
        try:
            if sondehub.enabled:
                sondehub.upload(data)
                telemetry_data['cloud_status']['sondehub'] = 'enabled'
        except Exception as e:
            app.logger.error(f"Sondehub error: {e}")
            telemetry_data['cloud_status']['sondehub'] = 'error'
        
        print(f"[DATA] Packet {telemetry_data['packet_count']}: Alt={data['altitude']}m, Status={data['status']}")
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
    print("  TuniLoon Ground Station – All Sprints + Security")
    print("  http://localhost:5000")
    print("=" * 60)
    print()
    print("[INFO] Cloud integrations:")
    print(f"  - Telegram: {'enabled' if telegram_bot.enabled else 'disabled'}")
    print()
    run_mock_consumer_thread()
    app.run(debug=False, host='0.0.0.0', port=5000)
