"""
FlightSimulator.py
Complete 2-hour flight simulation with full telemetry.
"""

import sys
import time
import json
import csv
import os
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from payload_simulator.src.MockPayload import MockPayload
from ground_station.src.Decoder import TelemetryDecoder
from ground_station.src.Logger import TelemetryLogger

class FlightSimulator:
    """Simulate a complete 2-hour balloon flight."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/settings.json"
        self.payload = MockPayload(config_path, continuous=False)
        self.decoder = TelemetryDecoder()
        self.logger = TelemetryLogger(data_dir="data/", filename="flight_simulation")
        
        # Flight metrics
        self.flight_data = []
        self.start_time = None
        self.end_time = None
        self.packet_count = 0
        self.max_altitude = 0
        self.min_temperature = 100
        self.max_temperature = -100
        
        # Statistics
        self.stats = {
            'total_packets': 0,
            'valid_packets': 0,
            'invalid_packets': 0,
            'max_altitude': 0,
            'max_altitude_time': None,
            'min_temperature': 0,
            'max_temperature': 0,
            'landing_time': None,
            'landing_location': None,
            'flight_duration': 0,
            'ascent_duration': 0,
            'descent_duration': 0
        }
    
    def run(self, interval: int = 30, verbose: bool = True):
        """
        Run the flight simulation.
        
        Args:
            interval: Transmission interval in seconds
            verbose: Print progress updates
        """
        print("=" * 70)
        print("  TuniLoon Flight Simulator")
        print("=" * 70)
        print()
        print(f"[INFO] Starting flight simulation")
        print(f"[INFO] Interval: {interval}s")
        print(f"[INFO] Flight duration: ~2 hours")
        print()
        
        # Generate flight path
        self.payload.generate_flight()
        flight_length = len(self.payload.flight_path)
        print(f"[INFO] Flight path generated with {flight_length} packets")
        
        self.start_time = datetime.now()
        last_status = None
        status_change_time = None
        
        print("\n[INFO] Starting flight...\n")
        
        for i in range(flight_length):
            # Get packet data
            data = self.payload.get_packet_data(i)
            if data is None:
                break
            
            # Pack the packet
            packet = self.payload.packer.pack_from_dict(data)
            
            # Decode to validate
            decoded = self.decoder.decode(packet)
            self.packet_count += 1
            
            if decoded is None:
                self.stats['invalid_packets'] += 1
                continue
            
            self.stats['valid_packets'] += 1
            
            # Store the data
            self.flight_data.append(decoded)
            self.logger.log(decoded)
            
            # Update metrics
            altitude = decoded['altitude']
            temperature = decoded['temperature']
            
            if altitude > self.stats['max_altitude']:
                self.stats['max_altitude'] = altitude
                self.stats['max_altitude_time'] = decoded['timestamp']
            
            if temperature < self.stats['min_temperature']:
                self.stats['min_temperature'] = temperature
            
            if temperature > self.stats['max_temperature']:
                self.stats['max_temperature'] = temperature
            
            # Track status changes
            status = decoded['status']
            if status != last_status:
                if last_status is not None:
                    print(f"[{i:3d}] Status changed: {last_status} → {status} at {altitude}m")
                last_status = status
            
            # Print progress
            if verbose and i % 20 == 0:
                status_map = {'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error'}
                status_text = status_map.get(status, status)
                print(f"[{i:3d}] Alt: {altitude:6.0f}m | Temp: {temperature:6.1f}°C | "
                      f"Status: {status_text}")
            
            # Check for landing
            if altitude < 10 and status == 'L' and self.stats['landing_time'] is None:
                self.stats['landing_time'] = decoded['timestamp']
                self.stats['landing_location'] = (decoded['latitude'], decoded['longitude'])
                print(f"\n🛬 LANDED at ({decoded['latitude']:.4f}, {decoded['longitude']:.4f})")
                break
            
            # Simulate transmission interval
            time.sleep(interval)
        
        self.end_time = datetime.now()
        self.stats['total_packets'] = self.packet_count
        self.stats['flight_duration'] = (self.end_time - self.start_time).total_seconds()
        
        # Calculate ascent/descent durations
        self._calculate_durations()
        
        # Close logger
        self.logger.close()
        
        print("\n" + "=" * 70)
        print("  Flight Simulation Complete!")
        print("=" * 70)
        self.print_stats()
        
        return self.stats
    
    def _calculate_durations(self):
        """Calculate ascent and descent durations."""
        if not self.flight_data:
            return
        
        # Find peak altitude
        peak_idx = 0
        peak_alt = 0
        for i, data in enumerate(self.flight_data):
            if data['altitude'] > peak_alt:
                peak_alt = data['altitude']
                peak_idx = i
        
        self.stats['ascent_duration'] = peak_idx * 30  # 30s interval
        self.stats['descent_duration'] = (len(self.flight_data) - peak_idx) * 30
    
    def print_stats(self):
        """Print flight statistics."""
        stats = self.stats
        
        print(f"\n📊 Flight Statistics:")
        print(f"  • Total packets sent:   {stats['total_packets']}")
        print(f"  • Valid packets:        {stats['valid_packets']}")
        print(f"  • Invalid packets:      {stats['invalid_packets']}")
        print(f"  • Max altitude:         {stats['max_altitude']:.0f}m")
        print(f"  • Min temperature:      {stats['min_temperature']:.1f}°C")
        print(f"  • Max temperature:      {stats['max_temperature']:.1f}°C")
        print(f"  • Flight duration:      {stats['flight_duration']:.0f}s")
        print(f"  • Ascent duration:      {stats['ascent_duration']:.0f}s")
        print(f"  • Descent duration:     {stats['descent_duration']:.0f}s")
        
        if stats['landing_location']:
            print(f"  • Landing location:     ({stats['landing_location'][0]:.4f}, {stats['landing_location'][1]:.4f})")
            print(f"  • Landing time:         {stats['landing_time']}")
    
    def generate_report(self, filename: str = None):
        """Generate a flight report."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/flight_report_{timestamp}.txt"
        
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("  TuniLoon Flight Report\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("📊 Flight Statistics:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total packets sent:   {self.stats['total_packets']}\n")
            f.write(f"Valid packets:        {self.stats['valid_packets']}\n")
            f.write(f"Invalid packets:      {self.stats['invalid_packets']}\n")
            f.write(f"Max altitude:         {self.stats['max_altitude']:.0f}m\n")
            f.write(f"Min temperature:      {self.stats['min_temperature']:.1f}°C\n")
            f.write(f"Max temperature:      {self.stats['max_temperature']:.1f}°C\n")
            f.write(f"Flight duration:      {self.stats['flight_duration']:.0f}s\n")
            f.write(f"Ascent duration:      {self.stats['ascent_duration']:.0f}s\n")
            f.write(f"Descent duration:     {self.stats['descent_duration']:.0f}s\n")
            
            if self.stats['landing_location']:
                f.write(f"Landing location:     ({self.stats['landing_location'][0]:.4f}, {self.stats['landing_location'][1]:.4f})\n")
                f.write(f"Landing time:         {self.stats['landing_time']}\n")
        
        print(f"\n[INFO] Report saved to {filename}")
        return filename


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=2,
                       help='Transmission interval in seconds (default: 2s for quick test)')
    parser.add_argument('--verbose', action='store_true',
                       help='Show all packets')
    args = parser.parse_args()
    
    sim = FlightSimulator()
    sim.run(interval=args.interval, verbose=args.verbose)
    sim.generate_report()
