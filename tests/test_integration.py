"""
test_integration.py
Integration tests for the full TuniLoon system.
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from payload_simulator.src.MockPayload import MockPayload
from ground_station.src.Decoder import TelemetryDecoder
from ground_station.src.Logger import TelemetryLogger


class TestIntegration(unittest.TestCase):
    """Integration test suite."""
    
    def test_full_flow(self):
        """Test full flow: Payload → Decoder → Logger."""
        print("\n[INFO] Running full flow integration test...")
        
        # Initialize components
        payload = MockPayload(continuous=False)
        decoder = TelemetryDecoder()
        logger = TelemetryLogger(data_dir="test_data/", filename="integration_test")
        
        # Generate flight
        payload.generate_flight()
        flight_points = payload.flight_path[:10]  # Test with first 10 points
        
        success_count = 0
        fail_count = 0
        
        for i, point in enumerate(flight_points):
            # Get data
            data = payload.get_packet_data(i)
            if data is None:
                fail_count += 1
                continue
            
            # Pack
            packet = payload.packer.pack_from_dict(data)
            
            # Decode
            decoded = decoder.decode(packet)
            if decoded is None:
                fail_count += 1
                continue
            
            # Log
            logger.log(decoded)
            success_count += 1
        
        logger.close()
        
        # Assert all succeeded
        self.assertEqual(fail_count, 0)
        self.assertEqual(success_count, len(flight_points))
        
        # Check CSV
        import os
        self.assertTrue(os.path.exists(logger.csv_path))
        
        # Check content
        with open(logger.csv_path, 'r') as f:
            lines = f.readlines()
            # Header + data rows
            self.assertEqual(len(lines), len(flight_points) + 1)
        
        print(f"[INFO] Integration test passed: {success_count}/{len(flight_points)} packets")
    
    def test_simulate_flight(self):
        """Test simulating a complete flight."""
        print("\n[INFO] Running flight simulation test...")
        
        payload = MockPayload(continuous=False)
        decoder = TelemetryDecoder()
        
        payload.generate_flight()
        
        total_packets = 0
        valid_packets = 0
        
        for i in range(len(payload.flight_path)):
            data = payload.get_packet_data(i)
            if data is None:
                break
            
            packet = payload.packer.pack_from_dict(data)
            decoded = decoder.decode(packet)
            
            total_packets += 1
            if decoded is not None:
                valid_packets += 1
        
        print(f"[INFO] Total packets: {total_packets}")
        print(f"[INFO] Valid packets: {valid_packets}")
        print(f"[INFO] Success rate: {valid_packets/total_packets*100:.1f}%")
        
        # Assert high success rate
        self.assertGreater(valid_packets / total_packets, 0.90)
    
    def test_end_to_end_with_logging(self):
        """Test end-to-end with CSV logging."""
        print("\n[INFO] Running end-to-end test with logging...")
        
        payload = MockPayload(continuous=False)
        decoder = TelemetryDecoder()
        logger = TelemetryLogger(data_dir="test_data/", filename="e2e_test")
        
        payload.generate_flight()
        
        for i in range(20):  # Test 20 packets
            data = payload.get_packet_data(i)
            if data is None:
                break
            
            packet = payload.packer.pack_from_dict(data)
            decoded = decoder.decode(packet)
            
            if decoded:
                logger.log(decoded)
        
        logger.close()
        
        # Verify CSV exists and has data
        import os
        self.assertTrue(os.path.exists(logger.csv_path))
        
        with open(logger.csv_path, 'r') as f:
            lines = f.readlines()
            # Header + at least 1 data row
            self.assertGreater(len(lines), 1)
        
        print(f"[INFO] End-to-end test passed: {len(lines)-1} packets logged")


if __name__ == '__main__':
    unittest.main()
