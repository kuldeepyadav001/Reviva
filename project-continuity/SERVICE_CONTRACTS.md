# Service contracts (locked for implementation)

All services FastAPI, internal :8000. Nginx prefixes `/api/<name>/`.

## ingest-service
- `GET /health`
- `POST /webhooks/razorpay` raw body, header `X-Razorpay-Signature`
  - 400 invalid HMAC (unless test secret unset — still hash if secret set)
  - 200 `{ok, deduped?}`
  - On `payment.failed`: persist then POST diagnosis `/diagnose`
- `POST /internal/events` — simulator inject (no HMAC; source=sim)

## simulator-service
- `GET /health`
- `POST /run-batch?n=100` → creates labeled events via ingest internal

## diagnosis-service
- `GET /health`
- `POST /diagnose` body: event fields → `{root_cause, retry_class, confidence, decision_source, reasoning}`

## policy-service
- `GET /health`
- `POST /decide` body: event + diagnosis → `{action_type, status, block_reason, playbook}`

## executor-service
- `GET /health`
- `POST /execute` body: event + decision → `{action_id, razorpay_ref, status}`
- Writes audit_log always
- `GET /audit?event_id=`
- `GET /metrics`

## dashboard (React)
Reads `/api/executor/metrics`, `/api/executor/audit/:id`, service health.
