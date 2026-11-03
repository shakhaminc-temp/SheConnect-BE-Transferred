from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.orm import relationship


class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)

    role = Column(String(50), default="SUPER_ADMIN")  # SUPER_ADMIN or INSTITUTE_ADMIN
    college_id = Column(Integer, ForeignKey("colleges.college_id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)

    college = relationship("College", foreign_keys=[college_id])


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    user_name = Column(String(150), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    location_name = Column(Text, nullable=True)
    accuracy = Column(Float, nullable=True)
    source = Column(String(100), nullable=True)

    status = Column(String(50), default="ACTIVE")  # ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_ALARM
    resolved_by = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("Admin", foreign_keys=[resolved_by])
