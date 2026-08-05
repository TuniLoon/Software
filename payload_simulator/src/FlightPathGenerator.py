"""
FlightPathGenerator.py
Generates a realistic high-altitude balloon flight path.

The path includes:
- Launch from Sousse, Tunisia
- Ascent to 30,000m over ~90 minutes
- Wind drift based on altitude
- Descent over ~30 minutes
- Landing southeast of launch (wind drift)
"""

import math
import csv
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

class FlightPathGenerator:
    """Generate simulated balloon flight path."""
    
    def __init__(self, config_path: str = None):
        """Initialize with optional config file."""
        self.launch_lat = 35.8276
        self.launch_lon = 10.6402
        
        # Flight parameters
        self.max_altitude = 30000  # meters
        self.ascent_rate = 5.0     # m/s (typical for weather balloons)
        self.descent_rate = 15.0   # m/s (faster due to parachute)
        self.total_time = 7200     # 2 hours in seconds
        
        # Wind drift coefficients (simplified)
        # Higher altitude = more drift
        self.wind_speed = 10.0  # m/s average
        self.wind_direction = 135  # degrees (southeast)
        
        # Load config if provided
        if config_path:
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'launch_site' in config:
                    self.launch_lat = config['launch_site']['latitude']
                    self.launch_lon = config['launch_site']['longitude']
                if 'max_altitude' in config['payload']:
                    self.max_altitude = config['payload']['max_altitude']
    
    def generate_flight_path(self, num_points: int = None) -> List[Dict]:
        """
        Generate flight path with timestamp, lat, lon, alt.
        
        Args:
            num_points: Number of data points (auto-calculated if None)
        
        Returns:
            List of dicts with keys: timestamp, latitude, longitude, altitude
        """
        if num_points is None:
            num_points = self.total_time // 30  # One point every 30 seconds
        
        points = []
        start_time = datetime.now()
        
        # Time step
        dt = self.total_time / num_points
        
        for i in range(num_points):
            t = i * dt
            
            # Calculate altitude
            if t < self.total_time * 0.75:  # Ascent phase (75% of time)
                alt = min(self.ascent_rate * t, self.max_altitude)
            else:  # Descent phase (25% of time)
                descent_time = t - (self.total_time * 0.75)
                alt = max(self.max_altitude - self.descent_rate * descent_time, 0)
            
            # Calculate wind drift
            # More drift at higher altitudes
            drift_factor = alt / self.max_altitude if alt > 0 else 0
            drift_speed = self.wind_speed * drift_factor
            
            # Convert wind direction to radians
            wind_rad = math.radians(self.wind_direction)
            dx = drift_speed * dt * math.sin(wind_rad)
            dy = drift_speed * dt * math.cos(wind_rad)
            
            # Convert meters to degrees (approximate)
            # 1 degree latitude ≈ 111,320 meters
            # 1 degree longitude ≈ 111,320 * cos(latitude) meters
            lat_change = dy / 111320
            lon_change = dx / (111320 * math.cos(math.radians(self.launch_lat)))
            
            # Apply changes
            lat = self.launch_lat + lat_change
            lon = self.launch_lon + lon_change
            
            # Add point
            points.append({
                'timestamp': (start_time + timedelta(seconds=t)).isoformat(),
                'timestamp_seconds': t,
                'latitude': round(lat, 6),
                'longitude': round(lon, 6),
                'altitude': round(alt, 0)
            })
        
        return points
    
    def save_to_csv(self, points: List[Dict], filename: str = None):
        """Save flight path to CSV file."""
        if filename is None:
            filename = f"flight_path_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'timestamp_seconds', 
                                                   'latitude', 'longitude', 'altitude'])
            writer.writeheader()
            writer.writerows(points)
        
        print(f"[INFO] Flight path saved to {filename}")
        return filename
    
    def get_flight_phase(self, altitude: float) -> str:
        """Determine flight phase based on altitude and time."""
        if altitude < 100:
            return 'L'  # Landing
        elif altitude > self.max_altitude - 1000:
            return 'D'  # Descent (past peak)
        else:
            return 'A'  # Ascent


if __name__ == "__main__":
    # Test the generator
    generator = FlightPathGenerator()
    path = generator.generate_flight_path(num_points=240)  # 2 hours, 30s intervals
    
    print(f"[INFO] Generated {len(path)} points")
    print(f"[INFO] Launch: ({path[0]['latitude']}, {path[0]['longitude']}) at {path[0]['altitude']}m")
    print(f"[INFO] Peak: max altitude = {max(p['altitude'] for p in path)}m")
    print(f"[INFO] Landing: ({path[-1]['latitude']}, {path[-1]['longitude']}) at {path[-1]['altitude']}m")
    
    # Save to CSV
    generator.save_to_csv(path)
