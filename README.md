# Reviva

Bounded recovery agent for Razorpay payment failures.

**Current build stage: 1 — foundation** (health only).

```bash
cp .env.example .env
docker compose up --build
curl -s http://localhost/health
curl -s http://localhost/api/ingest/health
```
