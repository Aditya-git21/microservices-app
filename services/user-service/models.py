from sqlalchemy import Column, String
from database import Base
from pydantic import BaseModel
from typing import Optional

# SQLAlchemy model — maps to DB table
class UserProfileDB(Base):
    __tablename__ = "profiles"
    username  = Column(String, primary_key=True, index=True)
    email     = Column(String, nullable=True)
    full_name = Column(String, nullable=True)

# Pydantic models — request/response
class UserProfile(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None