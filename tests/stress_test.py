"""
stress_test.py
24-hour stress test for the TuniLoon system.
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from payload_simulator.src.MockPayload import MockPayload
from ground_station.src.Decoder import TelemetryDecoder
from ground_station.src.Logger import TelemetryLogger

class StressTest:
    """Run a 24-hour stress test."""
    
    def __init__(self, duration_hours: int = 24):
        self.duration_hours = duration_hours
        self.payload = MockPayload(continuous=True)
        self.decoder = TelemetryDecoder()
        self.logger = TelemetryLogger(data_dir="data/", filename="stress_test")
        
        self.total_packets = 0
        self.valid_packets = 0
        self.invalid_packets = 0
        self.errors = []
        self.start_time = None
    
    def run(self, interval: int = 30):
        """
        Run the stress test.
        
        Args:
            interval: Packet interval in seconds
        """
        self.start_time = datetime.now()
        end_time = datetime.now() + timedelta(hours=self.duration_hours)
        
        print("=" * 70)
        print("  TuniLoon 24-Hour Stress Test")
        print("=" * 70)
        print()
        print(f"[INFO] Duration: {self.duration_hours} hours")
        print(f"[INFO] Interval: {interval}s")
        print(f"[INFO] Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[INFO] End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.payload.generate_flight()
        
        try:
            packet_index = 0
            while datetime.now() < end_time:
                data = self.payload.get_packet_data(packet_index)
                if data is None:
                    self.payload.generate_flight()
                    packet_index = 0
                    continue
                
                packet = self.payload.packer.pack_from_dict(data)
                decoded = self.decoder.decode(packet)
                
                self.total_packets += 1
                
                if decoded is None:
                    self.invalid_packets += 1
                else:
                    self.valid_packets += 1
                    self.logger.log(decoded)
                
                # Log progress every 100 packets
                if self.total_packets % 100 == 0:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    rate = self.total_packets / elapsed if elapsed > 0 else 0
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Packets: {self.total_packets}, "
                          f"Valid: {self.valid_packets}, "
                          f"Rate: {rate:.1f}/s")
                
                packet_index += 1
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n[INFO] Stress test stopped by user")
        
        self._print_summary()
        self.logger.close()
    
    def _print_summary(self):
        """Print test summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
        
        print("\n" + "=" * 70)
        print("  Stress Test Summary")
        print("=" * 70)
        print(f"\n  Duration: {elapsed:.2f} hours")
        print(f"  Total packets: {self.total_packets}")
        print(f"  Valid packets: {self.valid_packets}")
        print(f"  Invalid packets: {self.invalid_packets}")
        print(f"  Success rate: {self.valid_packets/self.total_packets*100:.2f}%" if self.total_packets > 0 else "  No packets sent")
        print(f"  Packet rate: {self.total_packets/elapsed:.2f}/hour")


if __name__ == "__main__":
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--hours', type=int, default=1,
                       help='Duration in hours (default: 1 for testing)')
    parser.add_argument('--interval', type=int, default=30,
                       help='Packet interval in seconds (default: 30)')
    args = parser.parse_args()
    
    test = StressTest(duration_hours=args.hours)
    test.run(interval=args.interval)
