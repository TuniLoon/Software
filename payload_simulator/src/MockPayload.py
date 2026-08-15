"""
MockPayload.py
Main mock payload simulator with real-time mode and continuous flight.
"""

import time
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from src.FlightPathGenerator import FlightPathGenerator
from src.SensorSimulator import SensorSimulator
from src.TelemetryPacker import TelemetryPacker

class MockPayload:
    def __init__(self, config_path: str = None, continuous: bool = True):
        self.config_path = config_path or "config/settings.json"
        self.continuous = continuous
        self.path_generator = FlightPathGenerator(config_path)
        self.sensor_simulator = SensorSimulator()
        self.packer = TelemetryPacker()
        self.flight_path = []
        self.packet_count = 0
        self.total_packets_sent = 0
        self.current_index = 0
        self.flight_cycle = 0
        self.last_altitude = None
        self.last_status = 'A'
        self.real_time = False

    def generate_flight(self):
        if self.flight_cycle > 0:
            self.path_generator.launch_lat += 0.0005 * (1 if self.flight_cycle % 2 == 0 else -1)
            self.path_generator.launch_lon += 0.0005 * (1 if self.flight_cycle % 2 == 0 else -1)
        self.flight_path = self.path_generator.generate_flight_path()
        self.flight_cycle += 1
        print(f"[INFO] Generated flight path #{self.flight_cycle} with {len(self.flight_path)} points")
        self.current_index = 0
        self.last_altitude = None
        return self.flight_path

    def determine_status(self, altitude):
        if altitude < 5:
            self.last_status = 'L'
            return 'L'
        if self.last_altitude is None:
            self.last_status = 'A'
            return 'A'
        delta = altitude - self.last_altitude
        if delta > 0.5:
            self.last_status = 'A'
        elif delta < -0.5:
            self.last_status = 'D'
        return self.last_status

    def get_next_packet(self):
        if not self.flight_path:
            self.generate_flight()
            self.current_index = 0
        if self.current_index >= len(self.flight_path):
            if self.continuous:
                self.generate_flight()
                self.current_index = 0
            else:
                return None
        point = self.flight_path[self.current_index]
        altitude = point['altitude']
        status = self.determine_status(altitude)
        self.last_altitude = altitude
        sensors = self.sensor_simulator.update(altitude, point['timestamp_seconds'])
        data = {
            'latitude': point['latitude'],
            'longitude': point['longitude'],
            'altitude': altitude,
            'pressure': sensors['pressure'],
            'temperature': sensors['temperature'],
            'humidity': sensors['humidity'],
            'thermal_avg': sensors['thermal_avg'],
            'status': status
        }
        self.current_index += 1
        return data

    def run(self, interval: int = 30, max_packets: int = None, verbose: bool = True, real_time: bool = False):
        if not self.flight_path:
            self.generate_flight()
        self.real_time = real_time
        print(f"[INFO] Starting mock payload simulation")
        print(f"[INFO] {'Real-time' if real_time else 'Fast'} mode")
        print(f"[INFO] Continuous mode: {'ON' if self.continuous else 'OFF'}")
        if max_packets:
            print(f"[INFO] Will stop after {max_packets} packets")
        try:
            while True:
                data = self.get_next_packet()
                if data is None:
                    if not self.continuous:
                        break
                    continue
                packet = self.packer.pack_from_dict(data)
                self.total_packets_sent += 1
                altitude = data['altitude']
                status = data['status']
                status_map = {'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error'}
                status_text = status_map.get(status, status)
                if verbose or self.total_packets_sent % 5 == 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Packet #{self.total_packets_sent}: "
                          f"Alt={altitude:.0f}m, Temp={data['temperature']:.1f}°C, "
                          f"Status={status_text} ({status})")
                if self.total_packets_sent % 10 == 0:
                    print(f"  → {packet}")
                if max_packets and self.total_packets_sent >= max_packets:
                    print(f"[INFO] Reached max packets ({max_packets}). Stopping.")
                    break
                # Sleep logic
                if real_time:
                    # In real-time, each packet represents 30 seconds of flight time.
                    # We need to wait 30 seconds between packets.
                    time.sleep(30)
                else:
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[INFO] Simulation stopped by user")
        print(f"[INFO] Total packets sent: {self.total_packets_sent}")
    def get_packet_data(self, time_index: int):
        """Get packet data at a specific time index."""
        self.current_index = time_index
        return self.get_next_packet()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--max-packets', type=int, default=None)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--real-time', action='store_true')
    args = parser.parse_args()
    payload = MockPayload(continuous=not args.once)
    payload.run(interval=args.interval, max_packets=args.max_packets, verbose=args.verbose, real_time=args.real_time)
