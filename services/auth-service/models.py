from sqlalchemy import Column, String
from database import Base
from pydantic import BaseModel

# SQLAlchemy model — maps to DB table
class UserDB(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)
    role     = Column(String, default="user")

# Pydantic models — for request/response validation
class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"