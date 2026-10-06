from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CarpoolRideCreate(BaseModel):
    start_location: str
    end_location: str
    departure_time: datetime
    total_seats: int
    price_per_seat: float
    tags: Optional[str] = None

class UserInfo(BaseModel):
    user_id: int
    name: Optional[str]
    email_id: str
    rating: Optional[float] = None

    class Config:
        from_attributes = True

class CarpoolRideResponse(BaseModel):
    ride_id: int
    driver_id: int
    start_location: str
    end_location: str
    departure_time: datetime
    total_seats: int
    available_seats: int
    price_per_seat: float
    status: str
    tags: Optional[str] = None
    created_at: datetime
    driver: Optional[UserInfo] = None

    class Config:
        from_attributes = True

class CarpoolRequestResponse(BaseModel):
    request_id: int
    ride_id: int
    rider_id: int
    status: str
    created_at: datetime
    ride: Optional[CarpoolRideResponse] = None
    rider: Optional[UserInfo] = None

    class Config:
        from_attributes = True

class CarpoolSeekCreate(BaseModel):
    start_location: str
    end_location: str
    departure_date: datetime

class CarpoolSeekResponse(BaseModel):
    seek_id: int
    rider_id: int
    start_location: str
    end_location: str
    departure_date: datetime
    status: str
    created_at: datetime
    rider: Optional[UserInfo] = None

    class Config:
        from_attributes = True

class PaymentInitializeResponse(BaseModel):
    order_id: str
    amount: float
    currency: str = "INR"
    request_id: int
