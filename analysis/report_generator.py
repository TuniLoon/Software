"""
report_generator.py
Generate a Markdown flight report.
"""

from datetime import datetime
from typing import Dict, List, Optional

class ReportGenerator:
    def __init__(self, metrics: Dict, wind_speed: float = None, wind_direction: float = None):
        self.metrics = metrics
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
    
    def generate_markdown(self) -> str:
        m = self.metrics
        lines = []
        lines.append("# TuniLoon Flight Report\n")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("## Flight Summary\n")
        lines.append("| Metric | Value |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Start Time | {m.get('start_time', 'N/A')} |")
        lines.append(f"| End Time | {m.get('end_time', 'N/A')} |")
        lines.append(f"| Duration | {m.get('duration_hours', 0):.2f} hours |")
        lines.append(f"| Max Altitude | {m.get('max_altitude', 0):.0f} m |")
        lines.append(f"| Min Altitude | {m.get('min_altitude', 0):.0f} m |")
        lines.append(f"| Max Temperature | {m.get('max_temperature', 0):.1f} °C |")
        lines.append(f"| Min Temperature | {m.get('min_temperature', 0):.1f} °C |")
        lines.append(f"| Avg Temperature | {m.get('avg_temperature', 0):.1f} °C |")
        lines.append(f"| Max Pressure | {m.get('max_pressure', 0):.1f} hPa |")
        lines.append(f"| Min Pressure | {m.get('min_pressure', 0):.1f} hPa |")
        lines.append(f"| Avg Ascent Rate | {m.get('avg_ascent_rate', 0):.1f} m/s |")
        lines.append(f"| Avg Descent Rate | {m.get('avg_descent_rate', 0):.1f} m/s |")
        lines.append(f"| Total Distance | {m.get('total_distance_km', 0):.2f} km |")
        lines.append(f"| Peak Location | {m.get('peak_location', (0,0))[0]:.4f}, {m.get('peak_location', (0,0))[1]:.4f} |")
        lines.append(f"| Peak Time | {m.get('peak_time', 'N/A')} |")
        lines.append(f"| Landing Location | {m.get('landing_location', (0,0))[0]:.4f}, {m.get('landing_location', (0,0))[1]:.4f} |")
        lines.append(f"| Landing Time | {m.get('landing_time', 'N/A')} |")
        if self.wind_speed is not None:
            lines.append(f"| Estimated Wind Speed | {self.wind_speed:.1f} m/s |")
            lines.append(f"| Estimated Wind Direction | {self.wind_direction:.1f}° |")
        lines.append("\n## Notes\n")
        lines.append("- This report was automatically generated from telemetry data.")
        lines.append("- All times are in local time.")
        return "\n".join(lines)
    
    def save_markdown(self, filename: str = None) -> str:
        if filename is None:
            filename = f"flight_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        content = self.generate_markdown()
        with open(filename, 'w') as f:
            f.write(content)
        print(f"[Report] Saved to {filename}")
        return filename

if __name__ == "__main__":
    sample_metrics = {
        'start_time': '2026-08-10T10:00:00',
        'end_time': '2026-08-10T12:00:00',
        'duration_hours': 2.0,
        'max_altitude': 30000,
        'min_altitude': 0,
        'max_temperature': 25.0,
        'min_temperature': -60.0,
        'avg_temperature': -10.0,
        'max_pressure': 1013,
        'min_pressure': 10,
        'avg_ascent_rate': 5.0,
        'avg_descent_rate': 15.0,
        'total_distance_km': 120.5,
        'peak_location': (35.8290, 10.6420),
        'peak_time': '2026-08-10T11:00:00',
        'landing_location': (35.8300, 10.6430),
        'landing_time': '2026-08-10T12:00:00'
    }
    report = ReportGenerator(sample_metrics, wind_speed=12.3, wind_direction=135)
    print(report.generate_markdown())
