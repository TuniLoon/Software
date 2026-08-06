"""
Decoder.py
Decode and validate telemetry packets.
"""

import time
from datetime import datetime
from typing import Dict, Optional, Tuple

class TelemetryDecoder:
    def __init__(self, identifier: str = "TUN"):
        self.identifier = identifier
        self.status_codes = {
            'A': 'Ascent',
            'D': 'Descent',
            'L': 'Landing',
            'E': 'Error',
            'F': 'Cut-down'
        }
    
    def compute_checksum(self, lat, lon, alt, press, temp, hum, thermal):
        eps = 1e-9
        sum_int = (int(round(lat * 10000 + eps)) + int(round(lon * 10000 + eps)) + int(alt) +
                   int(round(press * 10 + eps)) + int(round(temp * 10 + eps)) + int(round(hum * 10 + eps)) +
                   int(round(thermal * 10 + eps)))
        return sum_int % 10000
    
    def decode(self, packet: str) -> Optional[Dict]:
        try:
            parts = packet.strip().split(',')
            if len(parts) != 10:
                return None
            if parts[0] != self.identifier:
                return None
            if parts[9] not in self.status_codes:
                return None
            
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
            
            calculated = self.compute_checksum(
                data['latitude'], data['longitude'], data['altitude'],
                data['pressure'], data['temperature'], data['humidity'],
                data['thermal_avg']
            )
            
            if calculated != data['checksum']:
                return None
            
            return data
        except Exception:
            return None


if __name__ == "__main__":
    decoder = TelemetryDecoder()
    test_packets = [
        "TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,A",
        "TUN,36.8450,10.1220,5123,1005.8,-8.2,52.1,15.3,2694,D",
        "TUN,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,0826,L",
        "XXX,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,7058,L",
        "TUN,36.8460,10.1225,45,1013.5,25.3,58.7,12.1,9999,L",
    ]
    for packet in test_packets:
        result = decoder.decode(packet)
        if result:
            print(f"✅ Valid: Lat={result['latitude']}, Lon={result['longitude']}, Alt={result['altitude']}m, Status={result['status_description']}")
        else:
            print(f"❌ Invalid packet: {packet}")
