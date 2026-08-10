"""
multi_balloon.py
Manage multiple balloon trackers.
"""

from typing import Dict, List, Optional
from ground_station.src.balloon_tracker import BalloonTracker

class MultiBalloonManager:
    """Manager for multiple balloons."""
    
    def __init__(self):
        self.balloons = {}  # id -> BalloonTracker
        self.mqtt_topic = "tuniloon/telemetry"
    
    def add_balloon(self, balloon_id: str, name: str = None, color: str = None) -> BalloonTracker:
        """Add a new balloon tracker."""
        if balloon_id in self.balloons:
            return self.balloons[balloon_id]
        
        tracker = BalloonTracker(balloon_id, name, color)
        self.balloons[balloon_id] = tracker
        print(f"[MultiBalloon] Added balloon: {tracker.name} (ID: {balloon_id})")
        return tracker
    
    def remove_balloon(self, balloon_id: str):
        """Remove a balloon tracker."""
        if balloon_id in self.balloons:
            del self.balloons[balloon_id]
            print(f"[MultiBalloon] Removed balloon: {balloon_id}")
    
    def update_balloon(self, balloon_id: str, data: Dict):
        """Update a balloon with new telemetry."""
        if balloon_id not in self.balloons:
            # Auto-create if new balloon appears
            self.add_balloon(balloon_id)
        
        self.balloons[balloon_id].update(data)
    
    def get_balloon(self, balloon_id: str) -> Optional[BalloonTracker]:
        return self.balloons.get(balloon_id)
    
    def get_all_balloons(self) -> List[BalloonTracker]:
        return list(self.balloons.values())
    
    def get_active_balloons(self) -> List[BalloonTracker]:
        """Get balloons that have been updated in the last 60 seconds."""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(seconds=60)
        return [b for b in self.balloons.values() if b.last_update and b.last_update > cutoff]
    
    def get_offline_balloons(self) -> List[BalloonTracker]:
        """Get balloons that haven't updated in 60 seconds."""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(seconds=60)
        return [b for b in self.balloons.values() if not b.last_update or b.last_update <= cutoff]
    
    def get_balloon_count(self) -> int:
        return len(self.balloons)
    
    def get_all_data(self) -> Dict:
        """Get all balloon data as a dict for API responses."""
        return {
            balloon_id: tracker.to_dict()
            for balloon_id, tracker in self.balloons.items()
        }
    
    def get_summary(self) -> Dict:
        """Get a summary of all balloons."""
        balloons = self.get_all_balloons()
        return {
            'total': len(balloons),
            'active': len(self.get_active_balloons()),
            'offline': len(self.get_offline_balloons()),
            'balloons': [b.to_dict() for b in balloons]
        }
    
    def get_color_palette(self) -> List[str]:
        """Return a list of colors for new balloons."""
        return [
            '#ff6b35', '#00c853', '#2196f3', '#ff9800', '#9c27b0',
            '#f44336', '#4caf50', '#3f51b5', '#ff5722', '#009688',
            '#e91e63', '#8bc34a', '#00bcd4', '#ffc107', '#795548'
        ]
