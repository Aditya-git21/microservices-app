from pydantic import BaseModel

class Notification(BaseModel):
    username: str
    message: str
    event_type: str