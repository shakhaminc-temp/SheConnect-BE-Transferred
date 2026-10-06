import sys
import os
from datetime import datetime, timezone, timedelta

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.carpool import CarpoolRide, CarpoolSeek
from app.models.user import User

db = SessionLocal()

# Check what the datetime comparison returns
print("Checking timezone awareness:")
future_time = datetime.now() + timedelta(days=1)
aware_time = datetime.now(timezone.utc)
print(f"future_time: {future_time}")
print(f"aware_time: {aware_time}")

rides = db.query(CarpoolRide).all()
for r in rides:
    print(f"Ride: {r.ride_id}, start: {r.start_location}, end: {r.end_location}, time: {r.departure_time}, type: {type(r.departure_time)}")

# Try search query exactly like the backend
start_main = "Pune"
end_main = "Mumbai"

print("--- With timezone.utc ---")
rides_tz = db.query(CarpoolRide).filter(
    CarpoolRide.departure_time >= datetime.now(timezone.utc)
).all()
print(f"Found with tz: {len(rides_tz)}")

print("--- With utcnow (naive) ---")
rides_naive = db.query(CarpoolRide).filter(
    CarpoolRide.departure_time >= datetime.utcnow()
).all()
print(f"Found with naive: {len(rides_naive)}")

db.close()
