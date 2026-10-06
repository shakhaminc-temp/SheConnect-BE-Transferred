from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography


class Travel(Base):
    __tablename__ = "travels"

    travel_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    start_label = Column(String, nullable=False)
    end_label = Column(String, nullable=False)

    start_point = Column(Geography(geometry_type='POINT', srid=4326))
    end_point = Column(Geography(geometry_type='POINT', srid=4326))

    travel_date = Column(DateTime, nullable=False)
    mode_of_transport = Column(String, nullable=False)
    time_flex_minutes = Column(Integer, default=0)
    status = Column(String, default="SEARCHING")

    emergency_name = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    vehicle_no = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    deleted_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="travels")
    route = relationship("TravelRoute", uselist=False, back_populates="travel")
