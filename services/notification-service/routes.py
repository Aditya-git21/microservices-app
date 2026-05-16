from fastapi import APIRouter, Header
from models import Notification
from kafka_consumer import notifications_log
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.post("/notify", status_code=201)
def send_notification(notif: Notification):
    entry = {**notif.dict(), "sent_at": datetime.utcnow().isoformat()}
    notifications_log.append(entry)
    return {"message": f"Notification sent to {notif.username}", "entry": entry}

@router.get("/notifications/{username}")
def get_notifications(username: str, x_user: Optional[str] = Header(None)):
    return [n for n in notifications_log if n["username"] == username]