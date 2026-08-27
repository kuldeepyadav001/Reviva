# Phase 4 — Architecture (locked)

## System context
Reviva recovers failed Razorpay TEST payments for one merchant. It is not a gateway, not fraud, not live money.

Users: merchant ops (dashboard), Razorpay (webhooks), simulator (eval harness).

## Entities (Postgres source of truth)
- payment_events
- diagnoses
- recovery_actions
- audit_log (append-only)
- recoveries
- merchant_state (kill switch)

Redis: `evt:{payment_id}:{event}` 24h, `attempts:{cust}:{IST-date}`, `link:{cust}:{amount}`, `kill:{merchant}`, backoff keys.

## Data flow
```
Razorpay webhook OR simulator
    → nginx → ingest-service (HMAC, dedup, persist event)
    → HTTP POST diagnosis-service (rules then Ollama)
    → HTTP POST policy-service (playbook + gates)
    → HTTP POST executor-service (Razorpay test + audit_log)
    → dashboard reads via nginx → each service’s GET /metrics|/audit
```

Sync vs async: diagnosis/policy/execute are **sync HTTP** with timeouts. Retry **schedule** is Redis key + executor poll (not a second message bus).

## Components
| Service | Responsibility | Port internal |
|---|---|---|
| ingest-service | webhooks, persist, kick pipeline | 8000 |
| simulator-service | labeled batch, sim capture | 8000 |
| diagnosis-service | rules + Ollama | 8000 |
| policy-service | playbooks + stopping rules | 8000 |
| executor-service | Razorpay APIs + audit write | 8000 |
| dashboard | operator UI | 5173 / static |
| nginx | :80 edge | 80 |
| postgres, redis, ollama | data / cache / LLM | 5432 / 6379 / 11434 |

## State
- Truth: Postgres
- Ephemeral gates: Redis
- Kill switch: Redis + merchant_state row

## Failure modes
| Failure | Fallback |
|---|---|
| Bad HMAC | 400, no persist |
| Duplicate webhook | 200 deduped, no second action |
| Ollama down / bad JSON / conf&lt;0.6 | manual_review, no execute |
| Policy gate | action status blocked, still audit |
| Razorpay API down | action failed, audit, no retry storm |
| Service down mid-pipeline | ingest 5xx only if process not persisted; Razorpay will retry webhook → dedup protects |

Must never break in demo: compose up, ingest sim batch, dashboard load, audit click.

## Folder structure
```
reviva/
  docker-compose.yml nginx/ packages/shared/
  services/{ingest,simulator,diagnosis,policy,executor}-service/
  dashboard/
```

## Tech (1-line)
- FastAPI: you already ship it; async IO for webhooks
- SQLModel: one model for DB + API
- Postgres: audit durability
- Redis: idempotency/counters
- Ollama: local, no paid API
- Nginx: one origin for judges
- React later (Stage dashboard); Stage 1 static placeholder

## Why not
- Monolith: owner lock
- Kafka: solo ops death
- Paid LLM: cost + key in demo
