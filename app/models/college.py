from sqlalchemy import Column, Integer, String
from app.core.database import Base
from sqlalchemy.orm import relationship


class College(Base):
    __tablename__ = "colleges"

    college_id = Column(Integer, primary_key=True, index=True)
    college_name = Column(String(255), unique=True, nullable=False)

    users = relationship("User", back_populates="college")
