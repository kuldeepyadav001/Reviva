# Reviva

Bounded recovery agent for **Razorpay payment failures**.

DETECT → DIAGNOSE (rules first, Ollama only if unknown) → POLICY (stopping rules) → EXECUTE + AUDIT → MEASURE.

Six FastAPI services + React dashboard + Postgres + Redis + Nginx + Ollama.

₹ recovered on the dashboard is **seeded simulation** unless tagged live. Documented in API `note` fields.

## Run

```bash
cp .env.example .env
# add Razorpay TEST keys
docker compose up --build
cd dashboard && npm install && npm run build
# nginx serves dashboard/dist
```

- UI: http://localhost:8080/
- Ingest webhook: `POST /api/ingest/webhooks/razorpay`
- Batch: `POST /api/simulator/run-batch?n=100`

```bash
docker compose exec ollama ollama pull llama3.2:1b
pytest tests -q
```

## Stopping rules

Max 3 attempts/customer/IST day · quiet hours 21:00–09:00 IST · duplicate payment-link guard · amount > ₹10,000 approval · merchant kill-switch.

## Tests

```bash
pip install -e packages/shared pytest httpx respx fastapi sqlmodel
pytest tests -q
```
