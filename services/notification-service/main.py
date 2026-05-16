from fastapi import FastAPI
from routes import router
from tracing import setup_tracing
from kafka_consumer import consume_order_events
from prometheus_fastapi_instrumentator import Instrumentator
import logging, sys, asyncio

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"notification-service","msg":"%(message)s"}'
)

app = FastAPI(title="Notification Service", version="1.0")
setup_tracing(app, "notification-service")
app.include_router(router, prefix="/notif")
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_order_events())

@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}