"""
FlightReport.py
Generate a comprehensive flight report from CSV data.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

class FlightReport:
    """Generate flight report from CSV data."""
    
    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path
        self.data = []
        self.stats = {}
    
    def load_csv(self, csv_path: str):
        """Load data from CSV file."""
        self.csv_path = csv_path
        self.data = []
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                for key in ['latitude', 'longitude', 'altitude', 'pressure', 
                           'temperature', 'humidity', 'thermal_avg']:
                    if key in row:
                        row[key] = float(row[key])
                if 'timestamp_unix' in row:
                    row['timestamp_unix'] = float(row['timestamp_unix'])
                if 'checksum' in row:
                    row['checksum'] = int(row['checksum'])
                self.data.append(row)
        
        self._calculate_stats()
        return self.data
    
    def _calculate_stats(self):
        """Calculate flight statistics."""
        if not self.data:
            return
        
        altitudes = [d['altitude'] for d in self.data]
        temperatures = [d['temperature'] for d in self.data]
        
        self.stats = {
            'total_packets': len(self.data),
            'max_altitude': max(altitudes),
            'min_altitude': min(altitudes),
            'max_temperature': max(temperatures),
            'min_temperature': min(temperatures),
            'avg_temperature': sum(temperatures) / len(temperatures),
        }
        
        # Find landing (altitude < 10m)
        landing_packets = [d for d in self.data if d['altitude'] < 10]
        if landing_packets:
            landing = landing_packets[0]
            self.stats['landing_time'] = landing['timestamp']
            self.stats['landing_latitude'] = landing['latitude']
            self.stats['landing_longitude'] = landing['longitude']
    
    def generate_markdown(self, output_path: str = None):
        """Generate Markdown report."""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"data/flight_report_{timestamp}.md"
        
        Path('data').mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("# TuniLoon Flight Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Flight Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("| :--- | :--- |\n")
            f.write(f"| Total Packets | {self.stats.get('total_packets', 0)} |\n")
            f.write(f"| Max Altitude | {self.stats.get('max_altitude', 0):.0f} m |\n")
            f.write(f"| Min Altitude | {self.stats.get('min_altitude', 0):.0f} m |\n")
            f.write(f"| Max Temperature | {self.stats.get('max_temperature', 0):.1f} °C |\n")
            f.write(f"| Min Temperature | {self.stats.get('min_temperature', 0):.1f} °C |\n")
            f.write(f"| Avg Temperature | {self.stats.get('avg_temperature', 0):.1f} °C |\n")
            
            if 'landing_time' in self.stats:
                f.write(f"| Landing Time | {self.stats['landing_time']} |\n")
                f.write(f"| Landing Location | ({self.stats['landing_latitude']:.4f}, {self.stats['landing_longitude']:.4f}) |\n")
            
            f.write("\n## Data Sample\n\n")
            f.write("| Time | Altitude | Temperature | Status |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for d in self.data[:10]:
                f.write(f"| {d['timestamp']} | {d['altitude']:.0f}m | {d['temperature']:.1f}°C | {d['status']} |\n")
        
        print(f"[INFO] Report saved to {output_path}")
        return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        report = FlightReport()
        report.load_csv(csv_path)
        report.generate_markdown()
    else:
        print("Usage: python FlightReport.py <flight_data.csv>")
