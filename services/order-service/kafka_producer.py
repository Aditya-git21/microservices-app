import asyncio, json, logging, os
from aiokafka import AIOKafkaProducer
from sqlalchemy.orm import Session
from database import SessionLocal
from models import OutboxEvent

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = "order-events"

async def publish_order_event(event_type: str, order: dict):
    """Writes event to outbox table — Kafka publish happens via worker."""
    db: Session = SessionLocal()
    try:
        event = OutboxEvent(
            event_type=event_type,
            payload=json.dumps(order),
            processed=False
        )
        db.add(event)
        db.commit()
        logger.info(f"[Outbox] Event saved: {event_type} for order {order.get('order_id')}")
    finally:
        db.close()

async def outbox_worker():
    """Background worker — reads unprocessed outbox events, publishes to Kafka."""
    logger.info("[OutboxWorker] Starting...")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await producer.start()
    logger.info("[OutboxWorker] Kafka producer connected")

    while True:
        db: Session = SessionLocal()
        try:
            # Pick up to 10 unprocessed events
            events = db.query(OutboxEvent)\
                       .filter(OutboxEvent.processed == False)\
                       .order_by(OutboxEvent.created_at)\
                       .limit(10)\
                       .all()

            for event in events:
                try:
                    await producer.send_and_wait(
                        TOPIC,
                        json.dumps({
                            "event_type": event.event_type,
                            "payload": json.loads(event.payload)
                        }).encode("utf-8")
                    )
                    event.processed = True
                    db.commit()
                    logger.info(f"[OutboxWorker] Published event id={event.id} type={event.event_type}")
                except Exception as e:
                    logger.error(f"[OutboxWorker] Failed to publish event id={event.id}: {e}")

        except Exception as e:
            logger.error(f"[OutboxWorker] DB error: {e}")
        finally:
            db.close()

        await asyncio.sleep(2)    # poll every 2 seconds