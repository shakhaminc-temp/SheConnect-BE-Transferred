from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.core.database import Base

class CarpoolRide(Base):
    __tablename__ = "carpool_rides"

    ride_id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    start_location = Column(String, index=True, nullable=False)
    end_location = Column(String, index=True, nullable=False)
    departure_time = Column(DateTime, nullable=False)
    
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price_per_seat = Column(Float, nullable=False)
    
    status = Column(String, default="PROPOSED") # PROPOSED, COMPLETED, CANCELLED
    tags = Column(String, nullable=True) # Comma separated tags
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    driver = relationship("User", backref="carpool_rides")
    requests = relationship("CarpoolRequest", back_populates="ride")

class CarpoolRequest(Base):
    __tablename__ = "carpool_requests"

    request_id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("carpool_rides.ride_id"), nullable=False)
    rider_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED, PAID
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ride = relationship("CarpoolRide", back_populates="requests")
    rider = relationship("User", backref="carpool_requests")

class CarpoolSeek(Base):
    __tablename__ = "carpool_seeks"

    seek_id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    start_location = Column(String, index=True, nullable=False)
    end_location = Column(String, index=True, nullable=False)
    departure_date = Column(DateTime, nullable=False)
    
    status = Column(String, default="ACTIVE") # ACTIVE, FULFILLED, CANCELLED
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    rider = relationship("User", backref="carpool_seeks")

class CarpoolPayment(Base):
    __tablename__ = "carpool_payments"

    payment_id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("carpool_requests.request_id"), nullable=False, unique=True)
    
    amount = Column(Float, nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    
    status = Column(String, default="SUCCESS") # CREATED, SUCCESS, FAILED
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    request = relationship("CarpoolRequest", backref="payment")

class CarpoolChat(Base):
    __tablename__ = "carpool_chats"

    chat_id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("carpool_requests.request_id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    request = relationship("CarpoolRequest")
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
