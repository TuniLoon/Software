"""
Decoder.py
Decode and validate telemetry packets as defined in Sprint 0.3.
"""

import time
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

class TelemetryDecoder:
    """Decode and validate telemetry packets."""
    
    def __init__(self, identifier: str = "TUN"):
        self.identifier = identifier
        self.status_codes = {
            'A': 'Ascent',
            'D': 'Descent',
            'L': 'Landing',
            'E': 'Error',
            'F': 'Cut-down'
        }
    
    def compute_checksum(self, lat: float, lon: float, alt: float, 
                         press: float, temp: float, hum: float, 
                         thermal: float) -> int:
        """Calculate checksum according to protocol."""
        sum_int = (int(lat * 10000) + int(lon * 10000) + int(alt) +
                   int(press * 10) + int(temp * 10) + int(hum * 10) +
                   int(thermal * 10))
        return sum_int % 10000
    
    def validate(self, packet: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a packet without parsing.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Clean up
            packet = packet.strip()
            
            # Check length
            parts = packet.split(',')
            if len(parts) != 10:
                return False, f"Invalid field count: {len(parts)}, expected 10"
            
            # Check identifier
            if parts[0] != self.identifier:
                return False, f"Invalid identifier: {parts[0]}, expected {self.identifier}"
            
            # Check all fields are non-empty
            for i, part in enumerate(parts):
                if not part.strip():
                    return False, f"Empty field at position {i}"
            
            # Check status code
            if parts[9] not in self.status_codes:
                return False, f"Invalid status code: {parts[9]}"
            
            # Check numeric fields
            numeric_fields = [1, 2, 3, 4, 5, 6, 7, 8]
            for i in numeric_fields:
                try:
                    float(parts[i])
                except ValueError:
                    return False, f"Invalid number at position {i}: {parts[i]}"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def decode(self, packet: str) -> Optional[Dict]:
        """
        Decode and parse a telemetry packet.
        
        Args:
            packet: Raw packet string
        
        Returns:
            Dict with decoded data, or None if invalid
        """
        # Validate first
        is_valid, error = self.validate(packet)
        if not is_valid:
            print(f"[ERROR] Validation failed: {error}")
            return None
        
        try:
            parts = packet.strip().split(',')
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'timestamp_unix': time.time(),
                'identifier': parts[0],
                'latitude': float(parts[1]),
                'longitude': float(parts[2]),
                'altitude': int(float(parts[3])),
                'pressure': float(parts[4]),
                'temperature': float(parts[5]),
                'humidity': float(parts[6]),
                'thermal_avg': float(parts[7]),
                'checksum': int(parts[8]),
                'status': parts[9],
                'status_description': self.status_codes.get(parts[9], 'Unknown')
            }
            
            # Verify checksum
            calculated = self.compute_checksum(
                data['latitude'],
                data['longitude'],
                data['altitude'],
                data['pressure'],
                data['temperature'],
                data['humidity'],
                data['thermal_avg']
            )
            
            if calculated != data['checksum']:
                print(f"[ERROR] Checksum mismatch: got {data['checksum']}, "
                      f"expected {calculated}")
                return None
            
            return data
            
        except Exception as e:
            print(f"[ERROR] Decode error: {e}")
            return None
    
    def decode_raw(self, raw_string: str) -> Optional[Dict]:
        """Alias for decode()."""
        return self.decode(raw_string)


if __name__ == "__main__":
    # Test the decoder
    decoder = TelemetryDecoder()
    
    test_packets = [
        "TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,A",
        "TUN,36.8450,10.1220,5123,1005.8,-8.2,52.1,15.3,2694,D",
        "TUN,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,7058,L",
        "TUN,0.0000,0.0000,15234,1012.4,22.5,45.2,28.7,5977,E",
        "XXX,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,7058,L",  # Invalid
        "TUN,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,9999,L",  # Bad checksum
    ]
    
    for packet in test_packets:
        print(f"\n[TEST] Raw: {packet}")
        result = decoder.decode(packet)
        if result:
            print(f"[TEST] ✅ Valid: Lat={result['latitude']}, Lon={result['longitude']}, "
                  f"Alt={result['altitude']}m, Status={result['status_description']}")
        else:
            print(f"[TEST] ❌ Invalid packet")
