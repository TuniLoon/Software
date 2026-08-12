"""
historical_browser.py
Scan and index CSV files in the data/ directory.
"""

import os
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalBrowser:
    def __init__(self, data_dir: str = "data/"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_flights(self) -> List[Dict]:
        """Return list of all flight CSV files with metadata."""
        flights = []
        for csv_file in self.data_dir.glob("*.csv"):
            # Skip files that are not flight logs
            if csv_file.name.startswith("flight_") or csv_file.name.startswith("web_dashboard") or csv_file.name.startswith("flight_simulation"):
                meta = self._extract_metadata(csv_file)
                if meta:
                    flights.append(meta)
        # Sort by start time descending
        flights.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        return flights

    def _extract_metadata(self, csv_path: Path) -> Optional[Dict]:
        """Extract basic metadata from CSV (first and last rows)."""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if not rows:
                    logger.warning(f"No rows in {csv_path}")
                    return None

                # Detect column names (case-insensitive)
                fieldnames = reader.fieldnames or []
                def find_col(possible_names):
                    for name in possible_names:
                        if name in fieldnames:
                            return name
                    return None

                ts_col = find_col(['timestamp', 'time', 'datetime', 'Timestamp', 'Time'])
                alt_col = find_col(['altitude', 'alt', 'Altitude', 'Alt'])
                lat_col = find_col(['latitude', 'lat', 'Latitude', 'Lat'])
                lon_col = find_col(['longitude', 'lon', 'Longitude', 'Lon'])
                temp_col = find_col(['temperature', 'temp', 'Temperature', 'Temp'])

                # If essential columns missing, skip
                if not ts_col or not alt_col:
                    logger.warning(f"Missing timestamp or altitude column in {csv_path}")
                    return None

                # Get first and last rows
                first = rows[0]
                last = rows[-1]

                # Parse start time
                start_time = first.get(ts_col, '')
                end_time = last.get(ts_col, '')
                duration = None
                if start_time and end_time:
                    try:
                        # Try ISO format first
                        dt1 = datetime.fromisoformat(start_time)
                        dt2 = datetime.fromisoformat(end_time)
                        duration = (dt2 - dt1).total_seconds()
                    except:
                        try:
                            # Try common formats
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %I:%M:%S %p']:
                                try:
                                    dt1 = datetime.strptime(start_time, fmt)
                                    dt2 = datetime.strptime(end_time, fmt)
                                    duration = (dt2 - dt1).total_seconds()
                                    break
                                except:
                                    continue
                        except:
                            pass

                # Compute max altitude
                altitudes = []
                for row in rows:
                    try:
                        alt = float(row.get(alt_col, 0))
                        altitudes.append(alt)
                    except:
                        continue
                max_alt = max(altitudes) if altitudes else 0

                return {
                    'id': csv_path.stem,
                    'filename': csv_path.name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'max_altitude': max_alt,
                    'packet_count': len(rows),
                    'path': str(csv_path)
                }
        except Exception as e:
            logger.error(f"Error reading {csv_path}: {e}")
            return None

    def get_flight_data(self, flight_id: str) -> Optional[List[Dict]]:
        """Return all telemetry data for a given flight ID."""
        csv_path = self.data_dir / f"{flight_id}.csv"
        if not csv_path.exists():
            # Try with .json
            json_path = self.data_dir / f"{flight_id}.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
            return None
        # Read CSV
        data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                for key in ['latitude', 'longitude', 'altitude', 'pressure', 'temperature', 'humidity', 'thermal_avg']:
                    if key in row and row[key]:
                        try:
                            row[key] = float(row[key])
                        except:
                            pass
                if 'timestamp_unix' in row and row['timestamp_unix']:
                    try:
                        row['timestamp_unix'] = float(row['timestamp_unix'])
                    except:
                        pass
                if 'checksum' in row and row['checksum']:
                    try:
                        row['checksum'] = int(row['checksum'])
                    except:
                        pass
                data.append(row)
        return data

if __name__ == "__main__":
    browser = HistoricalBrowser()
    flights = browser.list_flights()
    for f in flights:
        print(f"ID: {f['id']}, Start: {f['start_time']}, Max Alt: {f['max_altitude']}")
