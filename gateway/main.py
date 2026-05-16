from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from circuit_breaker import breakers
from tracing import setup_tracing
import httpx, os, uuid, logging, sys, time

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"gateway","msg":"%(message)s"}'
)
logger = logging.getLogger(__name__)

AUTH_URL  = os.getenv("AUTH_SERVICE_URL",  "http://auth-service:8001")
USER_URL  = os.getenv("USER_SERVICE_URL",  "http://user-service:8002")
ORDER_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8003")
NOTIF_URL = os.getenv("NOTIF_SERVICE_URL", "http://notification-service:8004")

app = FastAPI(title="API Gateway", version="1.0")
setup_tracing(app, "gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

rate_limit_store: dict = {}
RATE_LIMIT  = 20
RATE_WINDOW = 60

def check_rate_limit(ip: str):
    now = time.time()
    hits = rate_limit_store.get(ip, [])
    hits = [t for t in hits if t > now - RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(429, f"Rate limit: {RATE_LIMIT} req/{RATE_WINDOW}s")
    hits.append(now)
    rate_limit_store[ip] = hits

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(f"path={request.url.path} method={request.method} status={response.status_code} duration_ms={duration}")
    return response

async def verify_token(token: str, request_id: str) -> dict:
    cb = breakers["auth"]
    if not cb.can_pass():
        raise HTTPException(503, "Auth service unavailable (circuit open)")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{AUTH_URL}/auth/verify",
                headers={"Authorization": f"Bearer {token}", "X-Request-ID": request_id},
                timeout=5.0
            )
        if resp.status_code == 200:
            cb.record_success()
            return resp.json()
        cb.record_failure()
        raise HTTPException(resp.status_code, resp.json().get("detail", "Auth failed"))
    except httpx.RequestError:
        cb.record_failure()
        raise HTTPException(503, "Auth service unreachable")

async def proxy(request: Request, target_url: str, service_name: str):
    cb = breakers[service_name]
    if not cb.can_pass():
        raise HTTPException(503, f"{service_name} unavailable (circuit open)")
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                timeout=10.0
            )
        cb.record_success()
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except httpx.RequestError as e:
        cb.record_failure()
        raise HTTPException(503, f"{service_name} unreachable: {str(e)}")

@app.post("/auth/register")
async def register(request: Request):
    check_rate_limit(request.client.host)
    return await proxy(request, f"{AUTH_URL}/auth/register", "auth")

@app.post("/auth/login")
async def login(request: Request):
    check_rate_limit(request.client.host)
    return await proxy(request, f"{AUTH_URL}/auth/login", "auth")

@app.post("/auth/refresh")
async def refresh(request: Request):
    return await proxy(request, f"{AUTH_URL}/auth/refresh", "auth")

@app.get("/users/profile/{username}")
async def get_profile(username: str, request: Request, token: str = Depends(oauth2_scheme)):
    user_info = await verify_token(token, request.state.request_id)
    headers = dict(request.headers)
    headers["x-user"] = user_info["username"]
    headers["x-role"] = user_info["role"]
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{USER_URL}/users/profile/{username}", headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.put("/users/profile/{username}")
async def update_profile(username: str, request: Request, token: str = Depends(oauth2_scheme)):
    user_info = await verify_token(token, request.state.request_id)
    body = await request.body()
    headers = dict(request.headers)
    headers["x-user"] = user_info["username"]
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.put(f"{USER_URL}/users/profile/{username}", content=body, headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.post("/orders")
async def create_order(request: Request, token: str = Depends(oauth2_scheme)):
    check_rate_limit(request.client.host)
    user_info = await verify_token(token, request.state.request_id)
    body = await request.body()
    headers = dict(request.headers)
    headers["x-user"] = user_info["username"]
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ORDER_URL}/orders-svc/orders", content=body, headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.get("/orders")
async def list_orders(request: Request, token: str = Depends(oauth2_scheme)):
    user_info = await verify_token(token, request.state.request_id)
    headers = dict(request.headers)
    headers["x-user"] = user_info["username"]
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{ORDER_URL}/orders-svc/orders", headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request, token: str = Depends(oauth2_scheme)):
    user_info = await verify_token(token, request.state.request_id)
    headers = dict(request.headers)
    headers["x-user"] = user_info["username"]
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{ORDER_URL}/orders-svc/orders/{order_id}", headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.get("/notifications/{username}")
async def get_notifications(username: str, request: Request, token: str = Depends(oauth2_scheme)):
    user_info = await verify_token(token, request.state.request_id)
    headers = dict(request.headers)
    headers["x-user"] = user_info["username"]
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{NOTIF_URL}/notif/notifications/{username}", headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.get("/admin/users")
async def admin_list_users(request: Request, token: str = Depends(oauth2_scheme)):
    user_info = await verify_token(token, request.state.request_id)
    if user_info["role"] != "admin":
        raise HTTPException(403, "Admin only")
    headers = dict(request.headers)
    headers["x-role"] = "admin"
    headers.pop("host", None)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{USER_URL}/users/users", headers=headers, timeout=10.0)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "gateway",
        "circuit_breakers": {name: cb.state.value for name, cb in breakers.items()}
    }