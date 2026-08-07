"""
visualize_anomalies.py
Visualize anomalies detected in telemetry data.
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict

class AnomalyVisualizer:
    """Visualize anomalies in telemetry data."""
    
    def __init__(self):
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
        self.ax_alt = self.axes[0, 0]
        self.ax_temp = self.axes[0, 1]
        self.ax_press = self.axes[1, 0]
        self.ax_status = self.axes[1, 1]
    
    def plot_data(self, data_points: List[Dict], anomalies: List[bool]):
        """
        Plot telemetry data with anomalies highlighted.
        
        Args:
            data_points: List of telemetry data dicts
            anomalies: List of boolean anomaly flags
        """
        if not data_points:
            print("[ML] No data to plot")
            return
        
        times = list(range(len(data_points)))
        altitudes = [p.get('altitude', 0) for p in data_points]
        temperatures = [p.get('temperature', 0) for p in data_points]
        pressures = [p.get('pressure', 0) for p in data_points]
        
        # Clear axes
        for ax in self.axes.flat:
            ax.clear()
        
        # Altitude plot
        self.ax_alt.plot(times, altitudes, 'b-', label='Altitude')
        self._highlight_anomalies(self.ax_alt, times, altitudes, anomalies)
        self.ax_alt.set_xlabel('Time (s)')
        self.ax_alt.set_ylabel('Altitude (m)')
        self.ax_alt.legend()
        self.ax_alt.grid(True, alpha=0.3)
        
        # Temperature plot
        self.ax_temp.plot(times, temperatures, 'r-', label='Temperature')
        self._highlight_anomalies(self.ax_temp, times, temperatures, anomalies)
        self.ax_temp.set_xlabel('Time (s)')
        self.ax_temp.set_ylabel('Temperature (°C)')
        self.ax_temp.legend()
        self.ax_temp.grid(True, alpha=0.3)
        
        # Pressure plot
        self.ax_press.plot(times, pressures, 'g-', label='Pressure')
        self._highlight_anomalies(self.ax_press, times, pressures, anomalies)
        self.ax_press.set_xlabel('Time (s)')
        self.ax_press.set_ylabel('Pressure (hPa)')
        self.ax_press.legend()
        self.ax_press.grid(True, alpha=0.3)
        
        # Status summary
        normal_count = sum(1 for a in anomalies if not a)
        anomaly_count = sum(1 for a in anomalies if a)
        colors = ['green' if not a else 'red' for a in anomalies]
        
        self.ax_status.bar(times, [1] * len(anomalies), color=colors, width=0.8)
        self.ax_status.set_xlabel('Time (s)')
        self.ax_status.set_ylabel('Status')
        self.ax_status.set_title(f'Anomalies: {anomaly_count} / {len(anomalies)}')
        self.ax_status.set_yticks([])
        self.ax_status.grid(True, alpha=0.3)
        
        plt.tight_layout()
    
    def _highlight_anomalies(self, ax, times, values, anomalies):
        """Highlight anomaly points on a plot."""
        anomaly_times = [times[i] for i, a in enumerate(anomalies) if a]
        anomaly_values = [values[i] for i, a in enumerate(anomalies) if a]
        
        if anomaly_times:
            ax.scatter(anomaly_times, anomaly_values, color='red', s=100, 
                      marker='x', zorder=5, label='Anomaly')
    
    def show(self):
        """Display the plot."""
        plt.show()
    
    def save(self, path: str = "ml/anomaly_plot.png"):
        """Save the plot to file."""
        plt.savefig(path, dpi=150, bbox_inches='tight')
        print(f"[ML] Plot saved to {path}")


if __name__ == "__main__":
    # Test the visualizer
    print("[TEST] Generating sample anomaly visualization...")
    
    # Generate sample data
    np.random.seed(42)
    n_points = 100
    
    # Normal altitude (smooth ascent)
    altitude = np.linspace(0, 30000, n_points) + np.random.normal(0, 100, n_points)
    # Add an anomaly (sudden drop)
    altitude[50:55] = 10000 + np.random.normal(0, 50, 5)
    
    temperature = 25 - altitude * 0.0065 + np.random.normal(0, 0.5, n_points)
    # Add an anomaly (sudden spike)
    temperature[70:75] = 10 + np.random.normal(0, 2, 5)
    
    pressure = 1013 * np.exp(-altitude / 8000) + np.random.normal(0, 5, n_points)
    
    # Anomaly flags
    anomalies = [False] * n_points
    for i in range(50, 55):
        anomalies[i] = True
    for i in range(70, 75):
        anomalies[i] = True
    
    data_points = [
        {'altitude': altitude[i], 'temperature': temperature[i], 
         'pressure': pressure[i], 'humidity': 50, 'thermal_avg': 20}
        for i in range(n_points)
    ]
    
    # Visualize
    visualizer = AnomalyVisualizer()
    visualizer.plot_data(data_points, anomalies)
    visualizer.save("ml/anomaly_plot.png")
    visualizer.show()
    
    print("[TEST] ✅ Visualization works!")
