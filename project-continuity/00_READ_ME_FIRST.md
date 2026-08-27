# READ ME FIRST — Reviva

Resume here, then `01_PROJECT_STATE.md`.

## Product
Bounded AI recovery agent for Razorpay payment failures (Track 3).

Loop: DETECT → DIAGNOSE → INTERVENE (gated) → EXECUTE + AUDIT → MEASURE.

## Locked by owner (do not silently change)
- **Six FastAPI services** + dashboard + postgres + redis + nginx + Ollama container
- Ollama as Docker Compose service
- Internship form: **6 months**, in-person Bangalore
- Python 3.11+, FastAPI, Pydantic v2, SQLModel
- Razorpay TEST mode only
- Solo Elite workflow: one phase/stage at a time, wait for confirmation

## Non-negotiable rules
1. No secrets in git. Env **names** only in `05_ACCOUNTS_AND_ENV.md`.
2. Rules before LLM. Known error codes never go to the model.
3. Policy engine owns actions. LLM never sends links.
4. Compliance gates cannot be bypassed.
5. Every money-adjacent action (including BLOCKED) writes `audit_log`.
6. Update `02_DECISIONS_LOG.md` in the same turn as the decision.
7. Do not collapse microservices unless the owner explicitly asks.

## Workflow position
See `01_PROJECT_STATE.md` for current phase.
