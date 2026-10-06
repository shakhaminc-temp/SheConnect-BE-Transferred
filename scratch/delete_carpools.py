import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models.carpool import CarpoolRide, CarpoolRequest, CarpoolSeek, CarpoolPayment, CarpoolChat

load_dotenv('.env')
DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("Deleting pending requests...")
pending_requests = db.query(CarpoolRequest).filter(CarpoolRequest.status.ilike("%PENDING%")).all()
for req in pending_requests:
    # also delete chats and payments related to this request if any
    db.query(CarpoolChat).filter(CarpoolChat.request_id == req.request_id).delete()
    db.query(CarpoolPayment).filter(CarpoolPayment.request_id == req.request_id).delete()
    print(f"Deleting Request {req.request_id} for Ride {req.ride_id}")
    db.delete(req)

print("Deleting proposed rides...")
proposed_rides = db.query(CarpoolRide).filter(CarpoolRide.status == "PROPOSED").all()
for ride in proposed_rides:
    # delete all requests of this ride before deleting the ride
    reqs = db.query(CarpoolRequest).filter(CarpoolRequest.ride_id == ride.ride_id).all()
    for req in reqs:
        db.query(CarpoolChat).filter(CarpoolChat.request_id == req.request_id).delete()
        db.query(CarpoolPayment).filter(CarpoolPayment.request_id == req.request_id).delete()
        db.delete(req)
    print(f"Deleting Ride {ride.ride_id} ({ride.start_location} -> {ride.end_location})")
    db.delete(ride)

print("Deleting active seeks...")
active_seeks = db.query(CarpoolSeek).filter(CarpoolSeek.status == "ACTIVE").all()
for seek in active_seeks:
    print(f"Deleting Seek {seek.seek_id} ({seek.start_location} -> {seek.end_location})")
    db.delete(seek)

db.commit()
print("Deletion complete.")
db.close()
