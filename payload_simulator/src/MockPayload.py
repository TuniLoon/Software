"""
MockPayload.py
Main script that simulates the balloon payload.

This script:
1. Generates a flight path
2. Simulates sensor readings
3. Packs telemetry packets
4. Sends them to a virtual COM port (or prints)
"""

import time
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.FlightPathGenerator import FlightPathGenerator
from src.SensorSimulator import SensorSimulator
from src.TelemetryPacker import TelemetryPacker


class MockPayload:
    """Main mock payload simulator."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/settings.json"
        self.load_config()
        
        # Initialize components
        self.path_generator = FlightPathGenerator(config_path)
        self.sensor_simulator = SensorSimulator()
        self.packer = TelemetryPacker(self.config.get('project', {}).get('identifier', 'TUN'))
        
        # Flight state
        self.current_time = 0
        self.is_running = False
        self.flight_path = []
        self.packet_count = 0
    
    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"[INFO] Config loaded from {self.config_path}")
        except FileNotFoundError:
            print(f"[WARN] Config not found, using defaults")
            self.config = {
                'payload': {
                    'transmission_interval': 30,
                    'max_altitude': 30000
                },
                'communication': {
                    'virtual_com_port': 'COM10',
                    'baud_rate': 115200
                }
            }
    
    def generate_flight(self):
        """Generate the complete flight path."""
        self.flight_path = self.path_generator.generate_flight_path()
        print(f"[INFO] Generated flight path with {len(self.flight_path)} points")
        return self.flight_path
    
    def get_status(self, altitude: float) -> str:
        """Determine status code for current altitude."""
        if altitude < 100:
            return 'L'
        elif altitude > 25000:
            return 'D'
        else:
            return 'A'
    
    def get_packet_data(self, time_index: int) -> dict:
        """Get packet data for a specific time index."""
        if time_index >= len(self.flight_path):
            return None
        
        point = self.flight_path[time_index]
        altitude = point['altitude']
        
        # Get sensor readings
        sensors = self.sensor_simulator.update(altitude, point['timestamp_seconds'])
        
        # Determine status
        status = self.get_status(altitude)
        
        return {
            'latitude': point['latitude'],
            'longitude': point['longitude'],
            'altitude': altitude,
            'pressure': sensors['pressure'],
            'temperature': sensors['temperature'],
            'humidity': sensors['humidity'],
            'thermal_avg': sensors['thermal_avg'],
            'status': status
        }
    
    def run(self, use_serial: bool = False, interval: int = 30):
        """
        Run the mock payload simulation.
        
        Args:
            use_serial: If True, send packets to virtual COM port
            interval: Transmission interval in seconds
        """
        self.is_running = True
        
        # Generate flight if not already done
        if not self.flight_path:
            self.generate_flight()
        
        print(f"[INFO] Starting mock payload simulation")
        print(f"[INFO] Transmission interval: {interval}s")
        print(f"[INFO] Total flight duration: ~{len(self.flight_path) * interval}s")
        
        # Open serial port if requested
        ser = None
        if use_serial:
            try:
                import serial
                com_port = self.config.get('communication', {}).get('virtual_com_port', 'COM10')
                baud = self.config.get('communication', {}).get('baud_rate', 115200)
                ser = serial.Serial(com_port, baud, timeout=1)
                print(f"[INFO] Connected to {com_port} at {baud} baud")
            except ImportError:
                print("[WARN] pyserial not installed, using print output instead")
                use_serial = False
            except Exception as e:
                print(f"[WARN] Could not open serial port: {e}")
                use_serial = False
        
        # Main loop
        try:
            for i, point in enumerate(self.flight_path):
                if not self.is_running:
                    break
                
                # Get packet data
                data = self.get_packet_data(i)
                if data is None:
                    break
                
                # Pack into telemetry packet
                packet = self.packer.pack_from_dict(data)
                self.packet_count += 1
                
                # Send or print
                timestamp = datetime.now().isoformat()
                if use_serial and ser:
                    ser.write(f"{packet}\n".encode())
                    print(f"[{timestamp}] SENT: {packet}")
                else:
                    print(f"[{timestamp}] {packet}")
                
                # Wait for next transmission
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n[INFO] Simulation stopped by user")
        
        finally:
            if ser:
                ser.close()
                print("[INFO] Serial port closed")
            
            print(f"[INFO] Total packets sent: {self.packet_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='TuniLoon Mock Payload Simulator')
    parser.add_argument('--serial', action='store_true', 
                       help='Send packets to virtual COM port')
    parser.add_argument('--interval', type=int, default=30,
                       help='Transmission interval in seconds (default: 30)')
    parser.add_argument('--config', type=str, default='config/settings.json',
                       help='Path to config file')
    
    args = parser.parse_args()
    
    # Create and run payload
    payload = MockPayload(args.config)
    payload.run(use_serial=args.serial, interval=args.interval)
