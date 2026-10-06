from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.carpool import CarpoolRide, CarpoolRequest, CarpoolPayment, CarpoolSeek
from app.schemas.carpool import (
    CarpoolRideCreate, CarpoolRideResponse, 
    CarpoolRequestResponse, PaymentInitializeResponse,
    CarpoolSeekCreate, CarpoolSeekResponse
)
from datetime import datetime, timezone
from typing import List
import uuid

router = APIRouter(prefix="/carpool", tags=["Carpooling"])

@router.post("/offer", response_model=CarpoolRideResponse)
def offer_ride(ride: CarpoolRideCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_ride = CarpoolRide(
        driver_id=current_user.user_id,
        start_location=ride.start_location,
        end_location=ride.end_location,
        departure_time=ride.departure_time,
        total_seats=ride.total_seats,
        available_seats=ride.total_seats,
        price_per_seat=ride.price_per_seat,
        tags=ride.tags,
        status="PROPOSED"
    )
    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return new_ride

@router.get("/search", response_model=List[CarpoolRideResponse])
def search_rides(
    start: str = Query(..., min_length=2),
    end: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    def get_keywords(loc: str):
        words = loc.replace(',', ' ').split()
        kw = [w.strip() for w in words if len(w.strip()) >= 3]
        return kw if kw else [loc.split(',')[0].strip()]
        
    start_words = get_keywords(start)
    end_words = get_keywords(end)
    
    start_conditions = [CarpoolRide.start_location.ilike(f"%{w}%") for w in start_words]
    end_conditions = [CarpoolRide.end_location.ilike(f"%{w}%") for w in end_words]
    
    rides = db.query(CarpoolRide).filter(
        or_(*start_conditions),
        or_(*end_conditions),
        CarpoolRide.status == "PROPOSED",
        CarpoolRide.available_seats > 0,
        CarpoolRide.departure_time >= datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
    ).options(joinedload(CarpoolRide.driver)).all()
    return rides

@router.post("/seek", response_model=CarpoolSeekResponse)
def create_seek(seek: CarpoolSeekCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.carpool import CarpoolSeek
    
    # Check if a similar active seek already exists to prevent spam
    existing = db.query(CarpoolSeek).filter(
        CarpoolSeek.rider_id == current_user.user_id,
        CarpoolSeek.status == "ACTIVE"
    ).first()
    
    if existing:
        # We can either reject or update. Let's just create a new one for simplicity or update existing
        pass

    new_seek = CarpoolSeek(
        rider_id=current_user.user_id,
        start_location=seek.start_location,
        end_location=seek.end_location,
        departure_date=seek.departure_date,
        status="ACTIVE"
    )
    db.add(new_seek)
    db.commit()
    db.refresh(new_seek)
    return new_seek

@router.get("/seek/search", response_model=List[CarpoolSeekResponse])
def search_seeks(
    start: str = Query(..., min_length=2),
    end: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Make matching more forgiving by taking the first part of the location string (before the comma)
    def get_keywords(loc: str):
        words = loc.replace(',', ' ').split()
        kw = [w.strip() for w in words if len(w.strip()) >= 3]
        return kw if kw else [loc.split(',')[0].strip()]
        
    start_words = get_keywords(start)
    end_words = get_keywords(end)
    
    start_conditions = [CarpoolSeek.start_location.ilike(f"%{w}%") for w in start_words]
    end_conditions = [CarpoolSeek.end_location.ilike(f"%{w}%") for w in end_words]
    
    seeks = db.query(CarpoolSeek).filter(
        or_(*start_conditions),
        or_(*end_conditions),
        CarpoolSeek.status == "ACTIVE",
        CarpoolSeek.departure_date >= datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
    ).options(joinedload(CarpoolSeek.rider)).all()
    return seeks

@router.get("/my-rides", response_model=List[CarpoolRideResponse])
def get_my_rides(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rides = db.query(CarpoolRide).options(joinedload(CarpoolRide.driver)).filter(CarpoolRide.driver_id == current_user.user_id).order_by(CarpoolRide.created_at.desc()).all()
    return rides

@router.post("/{ride_id}/request", response_model=CarpoolRequestResponse)
def request_ride(ride_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ride = db.query(CarpoolRide).filter(CarpoolRide.ride_id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot request your own ride")
    if ride.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No seats available")
        
    existing_request = db.query(CarpoolRequest).filter(
        CarpoolRequest.ride_id == ride_id,
        CarpoolRequest.rider_id == current_user.user_id
    ).first()
    if existing_request:
        raise HTTPException(status_code=400, detail="You already requested this ride")
        
    req = CarpoolRequest(
        ride_id=ride_id,
        rider_id=current_user.user_id,
        status="PENDING_DRIVER_APPROVAL" # Changed from PENDING to support two-way
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

@router.post("/{ride_id}/invite/{rider_id}", response_model=CarpoolRequestResponse)
def invite_rider(ride_id: int, rider_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ride = db.query(CarpoolRide).filter(CarpoolRide.ride_id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to invite to this ride")
    if ride.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No seats available")
        
    existing_request = db.query(CarpoolRequest).filter(
        CarpoolRequest.ride_id == ride_id,
        CarpoolRequest.rider_id == rider_id
    ).first()
    if existing_request:
        raise HTTPException(status_code=400, detail="Rider is already invited or requested")
        
    req = CarpoolRequest(
        ride_id=ride_id,
        rider_id=rider_id,
        status="PENDING_RIDER_APPROVAL"
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

@router.get("/my-requests", response_model=List[CarpoolRequestResponse])
def get_my_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reqs = db.query(CarpoolRequest).options(
        joinedload(CarpoolRequest.ride).joinedload(CarpoolRide.driver),
        joinedload(CarpoolRequest.rider)
    ).filter(CarpoolRequest.rider_id == current_user.user_id).order_by(CarpoolRequest.created_at.desc()).all()
    return reqs

@router.get("/{ride_id}/requests", response_model=List[CarpoolRequestResponse])
def get_ride_requests(ride_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ride = db.query(CarpoolRide).filter(CarpoolRide.ride_id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view requests for this ride")
        
    reqs = db.query(CarpoolRequest).options(
        joinedload(CarpoolRequest.ride).joinedload(CarpoolRide.driver),
        joinedload(CarpoolRequest.rider)
    ).filter(CarpoolRequest.ride_id == ride_id).order_by(CarpoolRequest.created_at.desc()).all()
    return reqs

@router.post("/request/{request_id}/approve", response_model=CarpoolRequestResponse)
def approve_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(CarpoolRequest).filter(CarpoolRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    ride = req.ride
    
    # If it's PENDING_DRIVER_APPROVAL, current_user must be driver
    if req.status == "PENDING_DRIVER_APPROVAL":
        if ride.driver_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to approve this request (Driver only)")
    # If it's PENDING_RIDER_APPROVAL, current_user must be rider
    elif req.status == "PENDING_RIDER_APPROVAL":
        if req.rider_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to approve this request (Rider only)")
    # If it was still "PENDING" (old data fallback), allow driver
    elif req.status == "PENDING":
        if ride.driver_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to approve this request")
    else:
        raise HTTPException(status_code=400, detail="Request is already processed or invalid status")
        
    if ride.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No seats available")
        
    req.status = "APPROVED"
    ride.available_seats -= 1
    
    # Also fulfill the rider's seek if they had one active for this route
    from app.models.carpool import CarpoolSeek
    seek = db.query(CarpoolSeek).filter(
        CarpoolSeek.rider_id == req.rider_id,
        CarpoolSeek.status == "ACTIVE"
    ).first()
    if seek:
        seek.status = "FULFILLED"
        
    db.commit()
    db.refresh(req)
    return req

@router.post("/request/{request_id}/pay", response_model=PaymentInitializeResponse)
def mock_pay_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(CarpoolRequest).filter(CarpoolRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.rider_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this request")
        
    if req.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Request must be APPROVED to make a payment")
        
    # Mocking razorpay order creation
    amount_in_paise = req.ride.price_per_seat * 100
    order_id = f"mock_order_{uuid.uuid4().hex[:10]}"
    
    payment = CarpoolPayment(
        request_id=req.request_id,
        amount=req.ride.price_per_seat,
        razorpay_order_id=order_id,
        status="SUCCESS" # Auto success for mock
    )
    req.status = "PAID"
    db.add(payment)
    db.commit()
    
    return PaymentInitializeResponse(
        order_id=order_id,
        amount=amount_in_paise,
        request_id=req.request_id
    )

@router.post("/{ride_id}/complete", response_model=CarpoolRideResponse)
def complete_ride(ride_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ride = db.query(CarpoolRide).filter(CarpoolRide.ride_id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to complete this ride")
        
    ride.status = "COMPLETED"
    db.commit()
    db.refresh(ride)
    return ride

from pydantic import BaseModel
class RateRequest(BaseModel):
    rating: int
    review: str = ""

@router.post("/{ride_id}/rate")
def rate_ride(ride_id: int, rate_data: RateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Mocking the rating mechanism. In a full implementation, this would save to a Ratings table.
    ride = db.query(CarpoolRide).filter(CarpoolRide.ride_id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    return {"message": "Rating submitted successfully", "rating": rate_data.rating}
