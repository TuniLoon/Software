"""
SensorSimulator.py
Generates simulated sensor data based on flight conditions.
"""

import random
import math

class SensorSimulator:
    """Simulate sensor readings for payload."""
    
    def __init__(self):
        self.temperature = 25.0    # °C (starting)
        self.pressure = 1013.25    # hPa (sea level)
        self.humidity = 60.0       # %
        self.thermal_avg = 30.0    # °C (ground temperature)
        
        # Environmental models
        self.temp_lapse_rate = 0.0065  # °C per meter (standard atmosphere)
        self.pressure_sea_level = 1013.25  # hPa
        
        # Noise parameters
        self.temp_noise = 0.5
        self.pressure_noise = 1.0
        self.humidity_noise = 2.0
        self.thermal_noise = 0.5
    
    def update(self, altitude: float, timestamp: float = 0) -> dict:
        """
        Generate sensor readings for given altitude.
        
        Args:
            altitude: Current altitude in meters
            timestamp: Elapsed time in seconds (for time-dependent effects)
        
        Returns:
            dict: Sensor readings with keys:
                  temperature, pressure, humidity, thermal_avg
        """
        # Temperature: Decreases with altitude (lapse rate)
        # At 30,000m, temperature is about -50°C
        temp = 25.0 - (altitude * self.temp_lapse_rate)
        temp = max(-60, min(60, temp))
        
        # Add noise
        temp += random.uniform(-self.temp_noise, self.temp_noise)
        temp = round(temp, 1)
        
        # Pressure: Exponential decrease with altitude
        # Standard atmosphere model
        if altitude < 11000:
            # Troposphere
            pressure = self.pressure_sea_level * math.pow(
                1 - (0.0065 * altitude) / 288.15, 5.2561
            )
        else:
            # Stratosphere (simplified)
            pressure = 226.32 * math.exp((11000 - altitude) / 6340)
        
        pressure = max(10, min(1100, pressure))
        pressure += random.uniform(-self.pressure_noise, self.pressure_noise)
        pressure = round(pressure, 1)
        
        # Humidity: Varies with altitude
        # Lower at high altitude
        if altitude < 1000:
            humidity = random.uniform(40, 80)
        elif altitude < 5000:
            humidity = random.uniform(20, 50)
        else:
            humidity = random.uniform(5, 30)
        
        humidity += random.uniform(-self.humidity_noise, self.humidity_noise)
        humidity = max(0, min(100, humidity))
        humidity = round(humidity, 1)
        
        # Thermal camera (ground temperature)
        # Warmer at lower altitude (closer to ground)
        thermal = 25.0 - (altitude / 1000) * 0.3
        thermal += random.uniform(-self.thermal_noise, self.thermal_noise)
        thermal = max(-10, min(45, thermal))
        thermal = round(thermal, 1)
        
        return {
            'temperature': temp,
            'pressure': pressure,
            'humidity': humidity,
            'thermal_avg': thermal
        }


if __name__ == "__main__":
    # Test the simulator
    simulator = SensorSimulator()
    
    # Test at different altitudes
    altitudes = [0, 1000, 5000, 15000, 25000, 30000]
    
    print("Altitude (m) | Temp (°C) | Pressure (hPa) | Humidity (%) | Thermal (°C)")
    print("-" * 70)
    
    for alt in altitudes:
        data = simulator.update(alt)
        print(f"{alt:12d} | {data['temperature']:8.1f} | {data['pressure']:13.1f} | "
              f"{data['humidity']:12.1f} | {data['thermal_avg']:11.1f}")
