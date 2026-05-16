# Microservices Platform

An event-driven microservices platform built with production-grade patterns — fault tolerance, distributed tracing, async messaging, and CI/CD deployment to AWS.

## Architecture

React (3000)
│
▼
API Gateway (8000)
JWT · Rate Limit · Circuit Breaker · Correlation ID
│
├── Auth Service (8001) ──── auth-db (PostgreSQL)
├── User Service (8002) ──── user-db (PostgreSQL)
├── Order Service (8003) ─── order-db (PostgreSQL)
│        │
│     Outbox Pattern
│        │
│      Kafka (order-events topic)
│        │
└── Notification Service (8004)
Prometheus · Grafana · Jaeger · GitHub Actions · AWS ECR

## Why This Architecture

**Separate databases per service** — no shared state between services. Order service DB schema can change without touching auth or user service. Fault isolation — if order-db crashes, users can still login.

**Outbox pattern** — order and Kafka event saved in one DB transaction. If Kafka is down, events queue up in the outbox table and publish when Kafka recovers. Zero message loss guaranteed.

**Circuit breaker** — gateway tracks failures per downstream service. After 3 failures, circuit opens and returns 503 immediately instead of waiting for timeout. Recovers automatically after 30 seconds.

**Idempotency** — every order request carries a client-generated key. Duplicate requests return the same order, never create duplicates. Handles network retries safely.

**Distributed tracing** — every request gets a trace ID propagated across all services. One search in Jaeger shows the full journey with per-service timing.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Database | PostgreSQL (one per service) |
| Messaging | Apache Kafka |
| Auth | JWT (access + refresh tokens) + RBAC |
| Tracing | OpenTelemetry + Jaeger |
| Metrics | Prometheus + Grafana |
| Container | Docker + docker-compose |
| CI/CD | GitHub Actions → AWS ECR |
| Frontend | React |

## Run Locally

```bash
# Start all services
cd infra
docker-compose up --build

# Register and login
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"adi","password":"secret123","role":"user"}'

# Save token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adi","password":"secret123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Place order
curl -X POST http://localhost:8000/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item":"laptop","quantity":1,"idempotency_key":"order-001"}'

# Check notification (fired automatically via Kafka)
curl http://localhost:8000/notifications/adi \
  -H "Authorization: Bearer $TOKEN"

# Start React frontend
cd frontend && npm start
```

## Services

| Service | Port | Responsibility |
|---|---|---|
| Gateway | 8000 | Auth, routing, rate limiting, circuit breaker |
| Auth | 8001 | Register, login, JWT issue/verify, refresh tokens |
| User | 8002 | User profiles, RBAC enforcement |
| Order | 8003 | Create/track orders, idempotency, outbox |
| Notification | 8004 | Kafka consumer, notification delivery |
| Prometheus | 9090 | Metrics scraping |
| Grafana | 3001 | Dashboards (admin/admin) |
| Jaeger | 16686 | Distributed tracing UI |

## Key Engineering Decisions

**Why Kafka over direct HTTP calls between services?**
Order service shouldn't care whether notification service is up. HTTP call creates tight coupling — slow notification service slows every order. Kafka decouples them completely. Order service fires an event and moves on.

**Why outbox pattern over direct Kafka publish?**
Direct publish after DB write has a failure window — DB succeeds, Kafka fails, event is lost. Outbox pattern wraps both in one transaction. A background worker polls the outbox and publishes. Even if Kafka is down for hours, no events are lost.

**Why idempotency keys?**
Networks are unreliable. A client may retry a request that actually succeeded. Without idempotency, that creates duplicate orders. The key lets the server detect and deduplicate retries safely.

**What would you add in production?**
- Redis for distributed rate limiting (current in-memory rate limiting doesn't scale across instances)
- AWS Secrets Manager instead of .env files
- Kubernetes with HPA for auto-scaling
- Dead letter queue for failed Kafka messages
- Proper integration test suite with Testcontainers

## CI/CD

Push to `main` → GitHub Actions builds Docker images for all 5 services → pushes to AWS ECR with commit SHA tag → every deployment is traceable to a specific commit.

## Observability

- **Metrics** — Prometheus scrapes all services every 15s. Open `http://localhost:9090`
- **Tracing** — Every request traced end-to-end. Open `http://localhost:16686`
- **Logs** — Structured JSON logs with correlation ID on every line across all services
