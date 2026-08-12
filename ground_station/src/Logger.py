"""
Logger.py
Save telemetry data to files (CSV and JSON).
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class TelemetryLogger:
    """Log telemetry data to files."""
    
    def __init__(self, data_dir: str = "data/", filename: str = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filename = f"flight_data_{timestamp}"
        else:
            self.filename = filename
        
        self.csv_path = self.data_dir / f"{self.filename}.csv"
        self.json_path = self.data_dir / f"{self.filename}.json"
        
        self.data_buffer = []
        self.csv_writer = None
        self.csv_file = None
        self.fieldnames = None
    
    def _init_csv(self, fieldnames: List[str]):
        """Initialize CSV file with dynamic headers."""
        self.fieldnames = fieldnames
        self.csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        self.csv_file.flush()
        print(f"[INFO] CSV logger initialized: {self.csv_path}")
    
    def log(self, data: Dict) -> bool:
        """Log a telemetry data point."""
        try:
            if self.csv_writer is None:
                fieldnames = list(data.keys())
                self._init_csv(fieldnames)
            
            self.csv_writer.writerow(data)
            self.csv_file.flush()
            self.data_buffer.append(data)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to log data: {e}")
            return False
    
    def log_batch(self, data_list: List[Dict]) -> int:
        count = 0
        for data in data_list:
            if self.log(data):
                count += 1
        return count
    
    def save_json(self) -> str:
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data_buffer, f, indent=2, ensure_ascii=False)
            print(f"[INFO] JSON saved: {self.json_path}")
            return str(self.json_path)
        except Exception as e:
            print(f"[ERROR] Failed to save JSON: {e}")
            return ""
    
    def close(self):
        if self.csv_file:
            self.csv_file.close()
            print(f"[INFO] CSV closed: {self.csv_path}")
    
    def get_stats(self) -> Dict:
        if not self.data_buffer:
            return {'count': 0}
        altitudes = [d.get('altitude', 0) for d in self.data_buffer]
        return {
            'count': len(self.data_buffer),
            'min_altitude': min(altitudes) if altitudes else 0,
            'max_altitude': max(altitudes) if altitudes else 0,
            'status_counts': {
                'Ascent': sum(1 for d in self.data_buffer if d.get('status') == 'A'),
                'Descent': sum(1 for d in self.data_buffer if d.get('status') == 'D'),
                'Landing': sum(1 for d in self.data_buffer if d.get('status') == 'L'),
                'Error': sum(1 for d in self.data_buffer if d.get('status') == 'E'),
                'Cut-down': sum(1 for d in self.data_buffer if d.get('status') == 'F')
            }
        }

if __name__ == "__main__":
    logger = TelemetryLogger(data_dir="test_data/", filename="test_flight")
    test_data = {
        'timestamp': '2024-11-15T10:00:00',
        'timestamp_unix': 1731679200,
        'identifier': 'TUN',
        'latitude': 36.8442,
        'longitude': 10.1213,
        'altitude': 15234,
        'pressure': 1012.4,
        'temperature': 22.5,
        'humidity': 45.2,
        'thermal_avg': 28.7,
        'checksum': 5977,
        'status': 'A',
        'status_description': 'Ascent'
    }
    logger.log(test_data)
    logger.save_json()
    stats = logger.get_stats()
    print(f"[INFO] Stats: {json.dumps(stats, indent=2)}")
    logger.close()
