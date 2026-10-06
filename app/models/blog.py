from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Text, String
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.orm import relationship


class Blog(Base):
    __tablename__ = "blogs"

    blog_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="blogs")
