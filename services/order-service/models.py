from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base
from pydantic import BaseModel
from enum import Enum

# Orders table
class OrderDB(Base):
    __tablename__ = "orders"
    order_id        = Column(String, primary_key=True, index=True)
    username        = Column(String, nullable=False)
    item            = Column(String, nullable=False)
    quantity        = Column(Integer, nullable=False)
    status          = Column(String, default="CONFIRMED")
    idempotency_key = Column(String, unique=True, nullable=False)

# Outbox table — this is the key addition
class OutboxEvent(Base):
    __tablename__ = "outbox"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    payload    = Column(String, nullable=False)    # JSON string
    processed  = Column(Boolean, default=False)    # False = waiting, True = published to Kafka
    created_at = Column(DateTime, server_default=func.now())

# Pydantic models
class OrderStatus(str, Enum):
    PENDING   = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED    = "FAILED"

class CreateOrderRequest(BaseModel):
    item: str
    quantity: int
    idempotency_key: str

class Order(BaseModel):
    order_id: str
    username: str
    item: str
    quantity: int
    status: OrderStatus