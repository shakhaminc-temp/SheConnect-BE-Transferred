import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env
load_dotenv('.env')
DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

from app.models.carpool import CarpoolRide, CarpoolRequest, CarpoolSeek

print("--- Carpool Rides ---")
rides = db.query(CarpoolRide).all()
for r in rides:
    print(f"Ride {r.ride_id}: {r.start_location} -> {r.end_location} (Status: {r.status})")

print("\n--- Carpool Seeks ---")
seeks = db.query(CarpoolSeek).all()
for s in seeks:
    print(f"Seek {s.seek_id}: {s.start_location} -> {s.end_location} (Status: {s.status})")

print("\n--- Carpool Requests ---")
requests = db.query(CarpoolRequest).all()
for req in requests:
    print(f"Request {req.request_id}: Ride ID {req.ride_id} (Status: {req.status})")

db.close()
