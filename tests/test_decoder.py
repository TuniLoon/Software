"""
test_decoder.py
Unit tests for the TelemetryDecoder.
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from ground_station.src.Decoder import TelemetryDecoder


class TestDecoder(unittest.TestCase):
    """Test suite for TelemetryDecoder."""
    
    def setUp(self):
        """Set up test environment."""
        self.decoder = TelemetryDecoder()
    
    def test_valid_packet(self):
        """Test decoding a valid packet."""
        packet = "TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,A"
        result = self.decoder.decode(packet)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['identifier'], 'TUN')
        self.assertEqual(result['latitude'], 36.8442)
        self.assertEqual(result['longitude'], 10.1213)
        self.assertEqual(result['altitude'], 15234)
        self.assertEqual(result['status'], 'A')
        self.assertEqual(result['status_description'], 'Ascent')
    
    def test_invalid_identifier(self):
        """Test packet with wrong identifier."""
        packet = "XXX,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,A"
        result = self.decoder.decode(packet)
        self.assertIsNone(result)
    
    def test_invalid_checksum(self):
        """Test packet with wrong checksum."""
        packet = "TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,9999,A"
        result = self.decoder.decode(packet)
        self.assertIsNone(result)
    
    def test_missing_fields(self):
        """Test packet with missing fields."""
        packet = "TUN,36.8442,10.1213,15234"
        result = self.decoder.decode(packet)
        self.assertIsNone(result)
    
    def test_landing_packet(self):
        """Test decoding a landing packet with correct checksum."""
        # Correct checksum for this data is 825 (due to floating-point rounding)
        packet = "TUN,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,0825,L"
        result = self.decoder.decode(packet)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['altitude'], 45)
        self.assertEqual(result['status'], 'L')
        self.assertEqual(result['status_description'], 'Landing')
    
    def test_error_packet(self):
        """Test decoding an error packet with correct checksum."""
        # Correct checksum for this data is 6322
        packet = "TUN,0.0000,0.0000,15234,1012.4,22.5,45.2,28.7,6322,E"
        result = self.decoder.decode(packet)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['latitude'], 0.0)
        self.assertEqual(result['longitude'], 0.0)
        self.assertEqual(result['status'], 'E')
        self.assertEqual(result['status_description'], 'Error')
    
    def test_status_codes(self):
        """Test all status codes are recognized."""
        statuses = ['A', 'D', 'L', 'E', 'F']
        for status in statuses:
            packet = f"TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,{status}"
            result = self.decoder.decode(packet)
            self.assertIsNotNone(result)
            self.assertEqual(result['status'], status)
    
    def test_checksum_calculation(self):
        """Test checksum calculation."""
        checksum = self.decoder.compute_checksum(36.8442, 10.1213, 15234, 1012.4, 22.5, 45.2, 28.7)
        self.assertEqual(checksum, 5977)


if __name__ == '__main__':
    unittest.main()
