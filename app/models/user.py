from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=True)   
    email_id = Column(String, unique=True, index=True, nullable=False)
    phone_no = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=True)  

    college_id = Column(
        Integer,
        ForeignKey("colleges.college_id"),
        nullable=True   
    )

    anonymous_id = Column(String)

    is_active = Column(Boolean, default=False) 
    is_verified = Column(Boolean, default=False)
    is_aadhaar_verified = Column(Boolean, default=False)

    last_otp_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True)

    travels = relationship("Travel", back_populates="user")
    blogs = relationship("Blog", back_populates="user")
    emergency_contacts = relationship("EmergencyContact", back_populates="user")

    college = relationship("College", back_populates="users")

    @property
    def rating(self) -> float:
        return round(4.0 + (self.user_id % 10) / 10.0, 1)
