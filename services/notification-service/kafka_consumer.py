import asyncio, json, logging, os
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = "order-events"

# In-memory log for Phase 3 (DB in Phase 5)
notifications_log: list = []

async def consume_order_events():
    """Listens to order-events topic and fires notifications."""
    logger.info("[KafkaConsumer] Starting...")
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="notification-group",       # consumer group — Kafka tracks offset per group
        auto_offset_reset="earliest"          # start from beginning if no offset stored
    )
    await consumer.start()
    logger.info("[KafkaConsumer] Connected, listening to order-events")

    try:
        async for msg in consumer:
            try:
                event = json.loads(msg.value.decode("utf-8"))
                event_type = event.get("event_type")
                payload    = event.get("payload", {})

                if event_type == "ORDER_PLACED":
                    notification = {
                        "username":   payload.get("username"),
                        "message":    f"Your order for {payload.get('item')} (qty: {payload.get('quantity')}) is confirmed!",
                        "event_type": event_type,
                        "order_id":   payload.get("order_id")
                    }
                    notifications_log.append(notification)
                    logger.info(f"[KafkaConsumer] Notification sent to {payload.get('username')} for order {payload.get('order_id')}")

            except Exception as e:
                logger.error(f"[KafkaConsumer] Failed to process message: {e}")
    finally:
        await consumer.stop()