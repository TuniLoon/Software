"""
Quick test for SQLite database.
"""

from ground_station.src.database import Database

db = Database()

# Show all flights
print("\n📋 Flights:")
flights = db.get_flights()
for f in flights:
    print(f"  ID {f['id']}: {f['start_time']} | packets: {f['packet_count']} | max alt: {f['max_altitude']}m")

# Show latest packet
latest = db.get_latest()
print(f"\n📌 Latest packet:")
if latest:
    print(f"  Alt: {latest.get('altitude')}m, Status: {latest.get('status')}, Time: {latest.get('timestamp')}")
else:
    print("  No data")

# Show last 5 packets
history = db.get_history(limit=5)
print(f"\n📜 Last 5 packets:")
for i, p in enumerate(history):
    print(f"  {i+1}. Alt: {p.get('altitude')}m, Status: {p.get('status')}")

# Count total packets
total = db.db_path
print(f"\n📊 Total packets in DB: {len(history)} (last 5 shown)")
