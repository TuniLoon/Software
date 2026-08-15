"""
database.py
SQLite database manager for telemetry storage.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

class Database:
    def __init__(self, db_path: str = "data/telemetry.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Flights table (group packets by session)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT,
                    end_time TEXT,
                    packet_count INTEGER DEFAULT 0,
                    max_altitude REAL DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            ''')
            # Telemetry table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flight_id INTEGER,
                    timestamp TEXT,
                    timestamp_unix REAL,
                    identifier TEXT,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    pressure REAL,
                    temperature REAL,
                    humidity REAL,
                    thermal_avg REAL,
                    checksum INTEGER,
                    status TEXT,
                    status_description TEXT,
                    anomaly INTEGER DEFAULT 0,
                    anomaly_score REAL DEFAULT 0,
                    anomaly_confidence REAL DEFAULT 0,
                    FOREIGN KEY(flight_id) REFERENCES flights(id)
                )
            ''')
            # Index for fast queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_telemetry_flight ON telemetry(flight_id)')
            conn.commit()

    def create_flight(self) -> int:
        """Create a new flight session and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO flights (start_time) VALUES (?)', (datetime.now().isoformat(),))
            conn.commit()
            return cursor.lastrowid

    def insert_telemetry(self, flight_id: int, data: Dict) -> int:
        """Insert a telemetry packet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO telemetry (
                    flight_id, timestamp, timestamp_unix, identifier,
                    latitude, longitude, altitude, pressure, temperature,
                    humidity, thermal_avg, checksum, status, status_description,
                    anomaly, anomaly_score, anomaly_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                flight_id,
                data.get('timestamp'),
                data.get('timestamp_unix'),
                data.get('identifier'),
                data.get('latitude'),
                data.get('longitude'),
                data.get('altitude'),
                data.get('pressure'),
                data.get('temperature'),
                data.get('humidity'),
                data.get('thermal_avg'),
                data.get('checksum'),
                data.get('status'),
                data.get('status_description'),
                int(data.get('anomaly', False)),
                data.get('anomaly_score', 0.0),
                data.get('anomaly_confidence', 0.0)
            ))
            # Update flight summary
            cursor.execute('''
                UPDATE flights SET
                    end_time = ?,
                    packet_count = packet_count + 1,
                    max_altitude = MAX(max_altitude, ?)
                WHERE id = ?
            ''', (data.get('timestamp'), data.get('altitude', 0), flight_id))
            conn.commit()
            return cursor.lastrowid

    def get_latest(self, flight_id: Optional[int] = None) -> Optional[Dict]:
        """Get the latest telemetry packet for a flight."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if flight_id is None:
                # Get latest flight
                cursor.execute('SELECT id FROM flights ORDER BY start_time DESC LIMIT 1')
                row = cursor.fetchone()
                if not row:
                    return None
                flight_id = row['id']
            cursor.execute('''
                SELECT * FROM telemetry
                WHERE flight_id = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (flight_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_history(self, flight_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Get recent telemetry packets for a flight."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if flight_id is None:
                cursor.execute('SELECT id FROM flights ORDER BY start_time DESC LIMIT 1')
                row = cursor.fetchone()
                if not row:
                    return []
                flight_id = row['id']
            cursor.execute('''
                SELECT * FROM telemetry
                WHERE flight_id = ?
                ORDER BY timestamp ASC LIMIT ?
            ''', (flight_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_flights(self) -> List[Dict]:
        """Return list of all flights."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, start_time, end_time, packet_count, max_altitude, status
                FROM flights
                ORDER BY start_time DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_flight(self, flight_id: int):
        """Delete a flight and its telemetry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM telemetry WHERE flight_id = ?', (flight_id,))
            cursor.execute('DELETE FROM flights WHERE id = ?', (flight_id,))
            conn.commit()

    def clear_all(self):
        """Clear all data (for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM telemetry')
            cursor.execute('DELETE FROM flights')
            conn.commit()
