from fastapi import FastAPI
from database import Base, engine
from routes import router
from tracing import setup_tracing
from prometheus_fastapi_instrumentator import Instrumentator
import logging, sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"auth-service","msg":"%(message)s"}'
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service", version="1.0")
setup_tracing(app, "auth-service")
app.include_router(router, prefix="/auth")
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}