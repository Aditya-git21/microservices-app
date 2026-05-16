from fastapi import FastAPI
from database import Base, engine
from routes import router
from tracing import setup_tracing
from kafka_producer import outbox_worker
from prometheus_fastapi_instrumentator import Instrumentator
import logging, sys, asyncio

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"order-service","msg":"%(message)s"}'
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order Service", version="1.0")
setup_tracing(app, "order-service")
app.include_router(router, prefix="/orders-svc")
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(outbox_worker())

@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}