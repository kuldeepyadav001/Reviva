# Reviva

**Bounded recovery for failed Razorpay payments.**

When a payment fails, most Indian customers never retry. Blind retries make it worse (down bank, empty balance, spam). Reviva **names the cause**, applies **hard stopping rules**, and only then talks to Razorpay — with an audit trail you can click.

> Narrative of the whole loop (webhooks vs Payment Links vs sim ₹): **[docs/HOW_REVIVA_WORKS.md](docs/HOW_REVIVA_WORKS.md)**

[![tests](https://github.com/kuldeepyadav001/Reviva/actions/workflows/test.yml/badge.svg)](https://github.com/kuldeepyadav001/Reviva/actions/workflows/test.yml)

---

## Why it exists

| Failure | Wrong move | Reviva |
|---|---|---|
| Issuer / switch down | Retry now | Backoff schedule |
| Insufficient funds | Retry now | Later window |
| 3DS / UPI PIN | Silent debit | **New** Payment Link (test) |
| Customer walked away | Email blast | **One** reminder, then stop |
| Amount &gt; ₹10,000 | Auto-send | Pending approval |

LLM classifies **only unknown payloads**. Known `error.reason` values never hit the model.

---

## Architecture

```
                    ┌─────────────┐
   labeled batch    │  simulator  │
                    └──────┬──────┘
                           ▼
┌─────────┐  HMAC/dedup  ┌─────────┐  rules→LLM  ┌───────────┐
│ Razorpay│─────────────►│ ingest  │────────────►│ diagnosis │
│ webhook │   (optional) └────┬────┘             └─────┬─────┘
└─────────┘                   │                        ▼
                              │                  ┌──────────┐
                              │                  │  policy  │  gates
                              │                  └────┬─────┘
                              ▼                       ▼
                       ┌────────────┐    ┌─────────────────────┐
                       │  dashboard │◄───│     executor        │
                       │  (React)   │    │  Payment Links test │
                       └────────────┘    │  append-only audit  │
                                         └─────────────────────┘
postgres · redis · nginx :8080 · ollama (qwen2.5:1.5b)
```

Six FastAPI services on Docker Compose. Same shape as a real payments sidecar — not a notebook.

---

## Run locally

Needs Docker Desktop + Node (dashboard build).

```bash
git clone https://github.com/kuldeepyadav001/Reviva.git
cd Reviva
cp .env.example .env
# RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET = TEST keys (rzp_test_…)
docker compose up --build
```

```bash
cd dashboard && npm install && npm run build
```

Open **http://localhost:8080/** → **Run labeled batch**.

Webhook URL is **not** required for the demo. Simulator injects `payment.failed`.

Ollama model (inside *this* compose project, not another app’s container):

```bash
docker compose exec ollama ollama pull qwen2.5:1.5b
```

---

## What a reviewer should click

1. All five health cards green.  
2. Batch of 20: mix of `schedule_retry_*`, `send_payment_link`, `pending_approval` (₹10k), maybe `manual_review`.  
3. An executed link row → audit JSON with `decision_source` like `rule:R_AUTH` and, if keys are set, `"stub": false` + `rzp.io` test checkout.  
4. ₹ on the dashboard is **seeded simulation**. The checkout page is real **test** Razorpay. Don’t confuse the two.

---

## Stopping rules (compliance)

- 3 attempts / customer / IST day  
- Quiet hours 21:00–09:00 IST  
- Duplicate Payment Link guard  
- &gt; ₹10,000 → approval  
- Merchant kill-switch  
- No SMS; no mail to `*.test` simulator addresses  

---

## Tests

```bash
pip install -e packages/shared pytest httpx respx fastapi sqlmodel pydantic-settings
pytest tests -q
```

CI runs the same suite on every push to `main`.

---

## Repo map

```
services/ingest-service      webhooks, dedup, pipeline
services/simulator-service   labeled evaluation harness
services/diagnosis-service   rules then Ollama
services/policy-service      playbooks + gates
services/executor-service    Razorpay + audit
packages/shared              models, HMAC, policy, Razorpay client
dashboard                    React operator UI
docs/HOW_REVIVA_WORKS.md     long explainer
tests/                       pytest
```

---

## Honest limitations

- Test mode. No live money.  
- Sim ₹ ≠ captured GMV.  
- Public webhook (ngrok) not required for clone-and-run.  
- Schema bootstrap is `create_all` with a race retry — fine for demo, not a migration product.

MIT © Kuldeep Yadav
