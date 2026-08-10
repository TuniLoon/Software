"""
balloon_tracker.py
Track a single balloon's telemetry.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

class BalloonTracker:
    """Track a single balloon."""
    
    def __init__(self, balloon_id: str, name: str = None, color: str = None):
        self.id = balloon_id
        self.name = name or f"Balloon-{balloon_id[:6]}"
        self.color = color or self._generate_color()
        
        self.latest = None
        self.history = []
        self.max_history = 500
        self.last_update = None
        self.status = 'offline'  # online, offline, error
    
    def _generate_color(self) -> str:
        """Generate a unique color based on ID."""
        import hashlib
        hash_val = int(hashlib.md5(self.id.encode()).hexdigest()[:6], 16)
        r = (hash_val >> 16) & 0xFF
        g = (hash_val >> 8) & 0xFF
        b = hash_val & 0xFF
        # Ensure colors are distinct (avoid dark colors)
        r = max(r, 100)
        g = max(g, 100)
        b = max(b, 100)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def update(self, data: Dict):
        """Update with new telemetry data."""
        self.latest = data
        self.history.append(data)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self.last_update = datetime.now()
        self.status = 'online'
    
    def get_latest(self) -> Optional[Dict]:
        return self.latest
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        return self.history[-limit:]
    
    def get_position(self) -> tuple:
        if self.latest:
            return (self.latest.get('latitude', 0), self.latest.get('longitude', 0))
        return (0, 0)
    
    def get_altitude(self) -> float:
        if self.latest:
            return self.latest.get('altitude', 0)
        return 0
    
    def get_status_text(self) -> str:
        status_map = {
            'A': 'Ascent',
            'D': 'Descent',
            'L': 'Landing',
            'E': 'Error',
            'F': 'Cut-down'
        }
        if self.latest:
            return status_map.get(self.latest.get('status', ''), 'Unknown')
        return 'Unknown'
    
    def to_dict(self) -> Dict:
        """Export balloon state as dict for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'status': self.status,
            'latest': self.latest,
            'history_count': len(self.history),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'altitude': self.get_altitude(),
            'position': self.get_position(),
            'status_text': self.get_status_text()
        }
