from fastapi import FastAPI
from database import Base, engine
from routes import router
from tracing import setup_tracing
from prometheus_fastapi_instrumentator import Instrumentator
import logging, sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"user-service","msg":"%(message)s"}'
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service", version="1.0")
setup_tracing(app, "user-service")
app.include_router(router, prefix="/users")
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "ok", "service": "user-service"}