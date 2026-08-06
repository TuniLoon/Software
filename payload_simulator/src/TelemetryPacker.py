"""
TelemetryPacker.py
Pack telemetry data according to the protocol.
"""

class TelemetryPacker:
    def __init__(self, identifier="TUN"):
        self.identifier = identifier
    
    def compute_checksum(self, lat, lon, alt, press, temp, hum, thermal):
        eps = 1e-9
        sum_int = (int(round(lat * 10000 + eps)) + int(round(lon * 10000 + eps)) + int(alt) +
                   int(round(press * 10 + eps)) + int(round(temp * 10 + eps)) + int(round(hum * 10 + eps)) +
                   int(round(thermal * 10 + eps)))
        return sum_int % 10000
    
    def pack(self, lat, lon, alt, press, temp, hum, thermal, status):
        checksum = self.compute_checksum(lat, lon, alt, press, temp, hum, thermal)
        packet = (f"{self.identifier},"
                  f"{lat:.4f},"
                  f"{lon:.4f},"
                  f"{int(alt):d},"
                  f"{press:.1f},"
                  f"{temp:.1f},"
                  f"{hum:.1f},"
                  f"{thermal:.1f},"
                  f"{checksum:04d},"
                  f"{status}")
        return packet
    
    def pack_from_dict(self, data_dict):
        return self.pack(
            data_dict['latitude'],
            data_dict['longitude'],
            data_dict['altitude'],
            data_dict['pressure'],
            data_dict['temperature'],
            data_dict['humidity'],
            data_dict['thermal_avg'],
            data_dict['status']
        )

if __name__ == "__main__":
    packer = TelemetryPacker()
    test_data = {
        'latitude': 36.8442,
        'longitude': 10.1213,
        'altitude': 15234,
        'pressure': 1012.4,
        'temperature': 22.5,
        'humidity': 45.2,
        'thermal_avg': 28.7,
        'status': 'A'
    }
    packet = packer.pack_from_dict(test_data)
    print(f"[INFO] Generated packet: {packet}")
