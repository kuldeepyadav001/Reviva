# Reviva

Bounded **payment-failure recovery** for Razorpay (test mode).

Detect → diagnose (rules first, local LLM only if unknown) → gated intervention → execute + audit → measure.

If the story is unclear, read **[docs/HOW_REVIVA_WORKS.md](docs/HOW_REVIVA_WORKS.md)** first.

## What problem it solves

Failed Razorpay payments leak merchant GMV. Blind retries make it worse (down bank, no funds, spam). Reviva names the **cause**, applies **stopping rules**, creates a **test Payment Link** only when that is the right move, and keeps an audit trail.

## Quick start

```bash
git clone https://github.com/kuldeepyadav001/Reviva.git
cd Reviva
cp .env.example .env
# set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET (TEST keys)
docker compose up --build
```

Other terminal:

```bash
cd dashboard && npm install && npm run build
```

- UI: **http://localhost:8080/**
- Health: `curl -s http://localhost:8080/api/ingest/health`

Optional (ambiguous diagnosis):

```bash
docker compose exec ollama ollama pull llama3.2:1b
```

Click **Run labeled batch**. Open a `send_*_link` row → audit. `stub: false` and `rzp.io` means a real **test** Payment Link.

You do **not** need a Razorpay webhook URL for this path. The simulator injects failures.

## Architecture

```
simulator ──► ingest ──► diagnosis ──► policy ──► executor ──► Razorpay Payment Links (test)
                 │                                              └── audit_log + metrics
                 └── dashboard (React) via nginx :8080
postgres · redis · ollama
```

Six FastAPI services. Shared models in `packages/shared`.

| Service | Role |
|---|---|
| ingest-service | HMAC webhooks + Redis dedup + sim ingest + pipeline kick |
| simulator-service | Labeled batch (40% NSF / 25% bank / 20% auth / 15% abandon) |
| diagnosis-service | Razorpay reason map, then Ollama JSON |
| policy-service | Playbooks + IST quiet hours, 3/day, dup-link, ₹10k, kill switch |
| executor-service | Payment Links + append-only audit + seeded ₹ (labeled sim) |
| dashboard | Operator console |

## Stopping rules (non-negotiable)

- Max 3 recovery attempts per customer per IST day  
- Quiet hours 21:00–09:00 IST  
- Duplicate Payment Link guard  
- Amount &gt; ₹10,000 → pending approval  
- Merchant kill-switch  
- No SMS; no email to `*.test` sim addresses  

## Tests

```bash
pip install -e packages/shared pytest httpx respx fastapi sqlmodel
pytest tests -q
```

## Honest metrics

Dashboard **₹ recovered** is **seeded simulation** unless you later wire `payment.captured`. The Payment Link on Razorpay’s page is real **test** checkout. Do not present sim ₹ as live GMV.

## Env (names only)

See `.env.example`. Never commit `.env`.

## License

Use as a student / demo project. Test mode only unless you explicitly change that.
