# Reviva

**Bounded recovery for failed Razorpay payments.**

When a payment fails, most Indian customers never retry. Blind retries make it worse (down bank, empty balance, spam). Reviva **names the cause**, applies **hard stopping rules**, and only then talks to Razorpay — with an audit trail you can click.

> Narrative of the whole loop (webhooks vs Payment Links vs sim ₹): **[docs/HOW_REVIVA_WORKS.md](docs/HOW_REVIVA_WORKS.md)**

[![tests](https://github.com/kuldeepyadav001/Reviva/actions/workflows/test.yml/badge.svg)](https://github.com/kuldeepyadav001/Reviva/actions/workflows/test.yml)

---

## The money problem (why this is not a toy)

Figures below are **industry / Razorpay-published research** used to size the problem. They are **not** Reviva’s live GMV. The dashboard ₹ is a **labeled simulation** so we can measure the agent, not a claim of production lift.

| Signal | Number | So what |
|---|---|---|
| Cart abandon caused by **payment failure** (India) | **~70%** | The cart is not “I don’t want it.” The **rail failed**. |
| Customers who **never retry** after **one** fail | **~70%** | One bad attempt ≈ lost order. Recovery has to happen **for** them. |
| Failures that are **bank / core-banking downtime** (peaks, legacy) | **~40%** | Instant retry hits the same down issuer. Need **backoff**. |
| Failures that are **user drop-off** | **~30%** | At most **one** reminder. More is spam. |
| Rest (auth, NSF, blocked instrument) | **~30%** | Each needs a **different** playbook, not one retry clock. |
| Well-designed **soft vs hard** retry | **15–20%** of failed txns recovered, **+3–5 pts** success rate | Only if NSF is not treated like timeout. |
| Stuck **UPI pending** | **~15%** of UPI; merchants lose **~40%** of that slice | Pending ≠ failed ≠ paid. Don’t lie to the merchant. |

**Merchant math (same brief):** ₹50 lakh/month attempted volume, **10%** margin, a **20-point** success-rate gap ≈ **₹1,00,000/month margin gone**. A **1-point** success drop costs on the order of **10×** a **0.1%** fee difference. Reliability beats shaving MDR.

RBI operational-resilience guidance (2024) makes “we retried blindly” a **compliance** issue, not just a conversion one.

### How Reviva turns those percentages into a system

| Mix we simulate (eval batch) | Policy |
|---|---|
| **40%** insufficient funds | Retry at a **balance window**, not now |
| **25%** bank downtime | **Exponential backoff** — never instant |
| **20%** auth failure | **Fresh** Razorpay Payment Link (new 3DS/UPI session) |
| **15%** abandonment | **Exactly one** reminder link, then **stop** |

Plus gates: 3 attempts/customer/IST day, quiet hours 21:00–09:00 IST, duplicate-link guard, **> ₹10,000** manual approval, merchant kill-switch. That is how 15–20% recovery stays **defensible** instead of becoming offense.

If this ran on a real ₹50L attempt book and even **1 point** of success came back, the brief’s own math says that can dwarf fee shopping. Reviva’s job is to make that lift **auditable** (rule id or LLM JSON on every row).

---

## Why the playbooks differ

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

Open **http://localhost:8080/** after `npm run build`.

**Hot reload (optional):** keep Compose running, then:

```bash
cd dashboard && npm run dev
```

Vite is on **http://localhost:5173** and proxies `/api` to nginx `:8080`. Use this while editing UI. Recruiters/clone-and-run still use port **8080**.

Webhook URL is **not** required for the demo. Simulator injects `payment.failed`.

`docker compose up --build` also runs **`ollama-pull`**, which downloads **qwen2.5:1.5b** into *this* stack (first time can take several minutes). Diagnosis is forced to `http://ollama:11434` even if `.env` still points at another machine.

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
