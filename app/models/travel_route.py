from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography


class TravelRoute(Base):
    __tablename__ = "travel_routes"

    route_id = Column(Integer, primary_key=True, index=True)
    travel_id = Column(Integer, ForeignKey("travels.travel_id"), nullable=False)

    route_geom = Column(Geography(geometry_type='LINESTRING', srid=4326))

    distance_meters = Column(Float)
    duration_seconds = Column(Float)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    travel = relationship("Travel", back_populates="route")
