# Accounts and env — NAMES ONLY

Never put secret values here.

## Providers (planned)
| Provider | Purpose |
|---|---|
| Razorpay TEST | Orders, payments, payment links, webhooks |
| Ollama (Docker) | LLM for unknown payloads only |
| PostgreSQL | Source of truth |
| Redis | Dedup, backoff, kill-switch, attempt counters |

## Env var names (planned)
```
REVIVA_ENV
DATABASE_URL
REDIS_URL
OLLAMA_BASE_URL
OLLAMA_MODEL
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
MERCHANT_ID
MERCHANT_KILL_SWITCH
TZ
```

Quality-gate commands: TBD after compose exists.
