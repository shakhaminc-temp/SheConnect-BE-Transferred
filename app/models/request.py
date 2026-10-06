from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.orm import relationship


class Request(Base):
    __tablename__ = "requests"

    request_id = Column(Integer, primary_key=True, index=True)

    sender_travel_id = Column(Integer, ForeignKey("travels.travel_id"), nullable=False)
    receiver_travel_id = Column(Integer, ForeignKey("travels.travel_id"), nullable=False)

    sent_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sent_to = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    status = Column(String, default="pending")
    # values: pending / accepted / rejected

    sender_privacy_mode = Column(String, default="ANONYMOUS")
    receiver_privacy_mode = Column(String, default="ANONYMOUS")
    # values: ANONYMOUS / LIMITED

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    deleted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    sender_travel = relationship("Travel", foreign_keys=[sender_travel_id])
    receiver_travel = relationship("Travel", foreign_keys=[receiver_travel_id])
    sender = relationship("User", foreign_keys=[sent_by])
    receiver = relationship("User", foreign_keys=[sent_to])
