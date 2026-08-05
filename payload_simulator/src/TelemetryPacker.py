"""
TelemetryPacker.py
Pack telemetry data according to Sprint 0.3 protocol.
"""

class TelemetryPacker:
    """Generate and pack telemetry data."""
    
    def __init__(self, identifier="TUN"):
        self.identifier = identifier
    
    def compute_checksum(self, lat, lon, alt, press, temp, hum, thermal):
        """Calculate checksum."""
        sum_int = (int(lat * 10000) + int(lon * 10000) + int(alt) +
                   int(press * 10) + int(temp * 10) + int(hum * 10) +
                   int(thermal * 10))
        return sum_int % 10000
    
    def pack(self, lat, lon, alt, press, temp, hum, thermal, status):
        """
        Pack telemetry data into a packet string.
        
        Args:
            lat: Latitude (float)
            lon: Longitude (float)
            alt: Altitude in meters (int)
            press: Pressure in hPa (float)
            temp: Temperature in °C (float)
            hum: Humidity in % (float)
            thermal: Thermal average in °C (float)
            status: Status code (A/D/L/E/F)
        
        Returns:
            str: Formatted packet string
        """
        # Calculate checksum
        checksum = self.compute_checksum(lat, lon, alt, press, temp, hum, thermal)
        
        # Format packet
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
        """Pack from a dictionary of data."""
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
    # Test the packer
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
    
    # Expected: TUN,36.8442,10.1213,15234,1012.4,22.5,45.2,28.7,5977,A
