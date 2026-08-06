"""
MockPayload.py
Main mock payload simulator with STABLE continuous mode.
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
        self.total_packets_sent = 0
        self.flight_cycle = 0
        
        # State tracking
        self.current_index = 0
        self.last_altitude = None
        self.last_status = 'A'
    
    def generate_flight(self):
        """Generate a new flight path."""
        if self.flight_cycle > 0:
            # Slight shift for variety
            self.path_generator.launch_lat += 0.0003 * (1 if self.flight_cycle % 2 == 0 else -1)
            self.path_generator.launch_lon += 0.0003 * (1 if self.flight_cycle % 2 == 0 else -1)
        
        self.flight_path = self.path_generator.generate_flight_path()
        self.flight_cycle += 1
        print(f"[INFO] Generated flight path #{self.flight_cycle} with {len(self.flight_path)} points")
        
        # Reset state for new flight
        self.current_index = 0
        self.last_altitude = None
        self.last_status = 'A'
        
        return self.flight_path
    
    def determine_status(self, altitude: float) -> str:
        """Determine status based on altitude change."""
        # Ground detection (only if consistently at 0m)
        if altitude < 5:
            # If we were descending and hit 0m, it's landing
            if self.last_status == 'D':
                self.last_status = 'L'
            else:
                self.last_status = 'L'
            return self.last_status
        
        if self.last_altitude is None:
            self.last_status = 'A'
            return 'A'
        
        delta = altitude - self.last_altitude
        
        if delta > 0.5:
            self.last_status = 'A'
        elif delta < -0.5:
            self.last_status = 'D'
        # else: stable – keep previous status
        
        return self.last_status
    
    def get_next_packet(self) -> dict:
        """Get the next packet in the sequence."""
        # If no flight path, generate one
        if not self.flight_path:
            self.generate_flight()
            self.current_index = 0
        
        # Check if we've reached the end of the flight path
        if self.current_index >= len(self.flight_path):
            if self.continuous:
                # Generate a new flight path
                self.generate_flight()
                self.current_index = 0
            else:
                return None
        
        # Get the current point
        point = self.flight_path[self.current_index]
        altitude = point['altitude']
        
        # Determine status
        status = self.determine_status(altitude)
        self.last_altitude = altitude
        
        # Get sensor readings
        sensors = self.sensor_simulator.update(altitude, point['timestamp_seconds'])
        
        # Build data
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
        
        # Increment index for next call
        self.current_index += 1
        
        return data
    
    def get_packet_data(self, time_index: int) -> dict:
        """Legacy method - use get_next_packet() instead."""
        # Set the index and get the packet
        self.current_index = time_index
        return self.get_next_packet()
    
    def run(self, interval: int = 30, max_packets: int = None, verbose: bool = True):
        """Run the simulation."""
        # Generate initial flight path
        self.generate_flight()
        
        print(f"[INFO] Starting mock payload simulation")
        print(f"[INFO] Transmission interval: {interval}s")
        print(f"[INFO] Continuous mode: {'ON' if self.continuous else 'OFF'}")
        print(f"[INFO] Flight length: {len(self.flight_path)} packets")
        
        if max_packets:
            print(f"[INFO] Will stop after {max_packets} packets")
        
        try:
            while True:
                # Get the next packet
                data = self.get_next_packet()
                
                if data is None:
                    if not self.continuous:
                        break
                    continue
                
                # Pack the data
                packet = self.packer.pack_from_dict(data)
                self.total_packets_sent += 1
                
                # Print packet info
                altitude = data['altitude']
                status = data['status']
                status_map = {'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error'}
                status_text = status_map.get(status, status)
                
                if verbose or self.total_packets_sent % 5 == 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Packet #{self.total_packets_sent}: "
                          f"Alt={altitude:.0f}m, Lat={data['latitude']:.4f}, "
                          f"Lon={data['longitude']:.4f}, Status={status_text} ({status})")
                
                # Show the raw packet occasionally
                if self.total_packets_sent % 10 == 0:
                    print(f"  → {packet}")
                
                # Check if we should stop
                if max_packets and self.total_packets_sent >= max_packets:
                    print(f"[INFO] Reached max packets ({max_packets}). Stopping.")
                    break
                
                # Wait for next transmission
                time.sleep(interval)
                    
        except KeyboardInterrupt:
            print("\n[INFO] Simulation stopped by user")
        
        print(f"[INFO] Total packets sent: {self.total_packets_sent}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=30,
                       help='Transmission interval in seconds')
    parser.add_argument('--max-packets', type=int, default=None,
                       help='Stop after N packets (for testing)')
    parser.add_argument('--once', action='store_true',
                       help='Run once (don\'t loop)')
    parser.add_argument('--verbose', action='store_true',
                       help='Show all packets')
    args = parser.parse_args()
    
    payload = MockPayload(continuous=not args.once)
    payload.run(interval=args.interval, max_packets=args.max_packets, verbose=args.verbose)
