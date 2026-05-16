from fastapi import APIRouter, HTTPException, Header, Depends
from models import OrderDB, CreateOrderRequest, Order, OrderStatus
from database import get_db
from kafka_producer import publish_order_event
from sqlalchemy.orm import Session
from typing import Optional
import uuid

router = APIRouter()

@router.post("/orders", response_model=Order, status_code=201)
async def create_order(req: CreateOrderRequest, db: Session = Depends(get_db), x_user: Optional[str] = Header(None)):
    if not x_user:
        raise HTTPException(401, "Missing X-User header")

    # Idempotency check
    existing = db.query(OrderDB).filter(OrderDB.idempotency_key == req.idempotency_key).first()
    if existing:
        return Order(
            order_id=existing.order_id,
            username=existing.username,
            item=existing.item,
            quantity=existing.quantity,
            status=existing.status
        )

    order_id = str(uuid.uuid4())
    order = OrderDB(
        order_id=order_id,
        username=x_user,
        item=req.item,
        quantity=req.quantity,
        status=OrderStatus.CONFIRMED,
        idempotency_key=req.idempotency_key
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Write to outbox — atomic with order save
    await publish_order_event("ORDER_PLACED", {
        "order_id": order.order_id,
        "username": order.username,
        "item":     order.item,
        "quantity": order.quantity
    })

    return Order(
        order_id=order.order_id,
        username=order.username,
        item=order.item,
        quantity=order.quantity,
        status=order.status
    )

@router.get("/orders", response_model=list[Order])
def list_orders(db: Session = Depends(get_db), x_user: Optional[str] = Header(None)):
    if not x_user:
        raise HTTPException(401, "Missing X-User header")
    orders = db.query(OrderDB).filter(OrderDB.username == x_user).all()
    return [Order(order_id=o.order_id, username=o.username, item=o.item, quantity=o.quantity, status=o.status) for o in orders]

@router.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str, db: Session = Depends(get_db), x_user: Optional[str] = Header(None)):
    order = db.query(OrderDB).filter(OrderDB.order_id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.username != x_user:
        raise HTTPException(403, "Not your order")
    return Order(order_id=order.order_id, username=order.username, item=order.item, quantity=order.quantity, status=order.status)