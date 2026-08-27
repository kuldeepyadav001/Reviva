# Reviva — what it is, in order

Read this if the UI and Razorpay page feel disconnected. They are two different pipes.

---

## 1. The problem (why this exists)

Indian checkout often **fails at payment**, not at “I don’t want the product.”

- A large share of cart abandon is **payment failure**.
- Many customers **do not try again** after one fail.
- Failures are not one type:
  - **Bank / switch down** (timeout, U28-class) → retrying *immediately* fails again.
  - **No money** → retrying now is useless; later (salary/top-up window) might work.
  - **PIN / 3DS failed** → customer must authenticate again (new session).
  - **They walked away** → at most **one** polite reminder, then stop.

If a merchant (or an “AI”) **spams retries and links**, that is harmful and, for this track, disqualifying.

**Reviva’s job:** see a failed payment, **name the cause**, pick a **legal** next step (or refuse), **prove why** in an audit log, and **measure** what a batch would recover.

It is **not** a second payment gateway. Razorpay still takes the money.

---

## 2. What “done” looks like (you already did this)

1. Simulator creates ~20 fake **failed payments** (labeled: funds / bank / auth / abandon).
2. **Ingest** stores them.
3. **Diagnosis** says *why* (rules first; LLM only if the error text is junk).
4. **Policy** says *what is allowed* (quiet hours, max 3 tries, ₹10k approval, kill switch).
5. **Executor** either schedules a retry **or** creates a **Razorpay Test Payment Link**.
6. You opened that link → **Razorpay’s test checkout**. That page is Razorpay, not Reviva.
7. Dashboard shows actions + audit. **₹ recovered** on the screen is still a **seeded simulation** unless someone actually pays the test link and we later mark capture. We labeled that on purpose.

---

## 3. The two Razorpay pipes (this is the part that was confusing)

```
PIPE A — “Someone tried to pay and it failed”
  Customer → Merchant checkout → Razorpay
  Razorpay → WEBHOOK → Reviva ingest
  (We did NOT use this in your demo. Simulator fakes these events.)

PIPE B — “Reviva asks the customer to try again, correctly”
  Reviva executor → Razorpay Payment Link API (your TEST keys)
  Razorpay → gives rzp.io URL
  Customer (you) opens URL → Razorpay test payment page
```

| | Webhook (Pipe A) | Payment Link (Pipe B) |
|---|---|---|
| Direction | Razorpay **calls us** | **We call** Razorpay |
| You needed it for the 20-batch? | **No** | Yes, for real `plink_…` |
| Why we skipped webhook | Needs public HTTPS (ngrok). Simulator replaces it. | Keys in `.env` + executor |

**Opening the Razorpay page does not mean the simulator “₹ recovered” updated.**  
That counter is RNG for the labeled batch. A **real** capture would be Pipe A again: `payment.captured` webhook (or we poll). We have not closed that live loop yet. That is OK for v1 demo if you say it out loud.

---

## 4. Walk one payment through our services

Example: auth failed (wrong UPI PIN / 3DS).

```
simulator-service
  “Here is a failed payment, ground truth = auth_failure”
        │
        ▼
ingest-service
  Save row. Dedup key so Razorpay retries don’t double-act.
        │  HTTP
        ▼
diagnosis-service
  Rule map: error_reason authentication_failed → auth_failure
  (Ollama is NOT called. That is the point.)
        │  HTTP
        ▼
policy-service
  Playbook: send_payment_link
  Gates: not night IST? under 3 tries? under ₹10,000? kill switch off?
  If a gate fails → status blocked / pending_approval. Still audited.
        │  HTTP
        ▼
executor-service
  Razorpay: create Payment Link (test)
  Write audit_log: who / what / rule id / amount / plink id
  Seeded RNG: “would this recover in sim?” → dashboard ₹
        │
        ▼
dashboard (React)
  You click the row → JSON audit chain
```

Other causes:

| Cause | Policy action |
|---|---|
| bank_downtime | `schedule_retry_backoff` — **never** instant retry |
| insufficient_funds | `schedule_retry_balance_window` — later window |
| auth_failure | `send_payment_link` |
| abandonment | `send_single_reminder_link` — **one**, then stop |
| unknown / low LLM confidence | `hold_manual_review` |
| amount > ₹10,000 | `pending_approval` even if cause is clear |

---

## 5. The six services (why they are separate)

You already shipped multi-service Docker apps. Judges can see the same pattern.

| Service | One sentence |
|---|---|
| **ingest** | Trust the event (HMAC if webhook) and don’t process twice. |
| **simulator** | Fake 100/20 failures with **labels** so we can score diagnosis. Not production traffic. |
| **diagnosis** | Rules for known Razorpay reasons; **Ollama only** for leftover junk. |
| **policy** | The law. LLM cannot send a link. |
| **executor** | Talk to Razorpay + append-only audit. |
| **dashboard** | Operator eyes: health, actions, blocked, ₹ sim, audit. |

Plus: **Postgres** (truth), **Redis** (dedup / attempt counts / kill switch), **Nginx** (one URL), **Ollama** (local model).

---

## 6. Problems we actually hit (and the lesson)

These are real. Use them in “what broke.”

1. **Docker `tls: bad record MAC`**  
   Image download corrupted. Retry / prune / no VPN. Not an app bug.

2. **Port 80 already taken**  
   Windows often binds 80. We moved Nginx to **8080**.

3. **Postgres `paymentevent` already exists**  
   Ingest and executor both `CREATE TABLE` at startup. Race. Fixed with retrying `create_all`.

4. **`plink_stub_…` even with keys in `.env`**  
   (a) Executor originally **never called** Razorpay — only stubs.  
   (b) Compose **does not** pick new `.env` until `down` + `up --build`.  
   (c) Clicking an **old** audit row still shows the stub. New rows after the fix showed `plink_TUn…` / `stub: false`.

5. **Webhook vs keys mix-up**  
   Keys are for **us calling Razorpay**. Webhook is for **Razorpay calling us**. Simulator batch does not need a webhook URL.

6. **LLM vs rules**  
   If we let the model guess “abandon” on a down bank, policy would send a link into a dead issuer. **Rules run first.** That’s the AI judgment story.

---

## 7. How Razorpay could put this *inside* their system

Reviva is a prototype of a **Recovery / Smart Retry** layer **on top of** Checkout.

**Today (you):** sidecar on a merchant laptop, test keys, Docker.

**Native Razorpay shape:**

1. **Ingest** becomes a first-party consumer of existing `payment.failed` (they already emit this). No ngrok.
2. **Diagnosis** maps their own `error.reason` / NPCI codes (Z9, U28, …) — they already document these. Rules stay in their error-mapping product; LLM only on long-tail descriptions.
3. **Policy** is a **merchant toggle**: max attempts, quiet hours in IST, “don’t email after 1 reminder,” high-value approval in Dashboard.
4. **Executor** uses **Payment Links / retry APIs they already have**, with the same compliance (no dark patterns, reminder_enable off unless the merchant opted in).
5. **Audit** is a Dashboard tab: “Why did Smart Retry fire?” — support and RBI-style explainability.
6. **Measure** is real: `payment.captured` on the **same** order/link, not our seeded RNG. That’s the production metric: **success-rate lift and ₹ recovered**.

They would **not** need our six containers. They would keep the **same state machine**: detect → classify (rules > model) → gated action → audit → measure.

What Reviva proves for them: **soft vs hard failure must not share one retry clock**, and **the model must not be allowed to spend customer attention**.

---

## 8. What we are honest about

- Simulator ₹ ≠ money in a bank.
- Test checkout ≠ live UPI debit.
- No public webhook yet → no live `payment.failed` from a real shop.
- Payment Links for `cN@example.test` do **not** send email (anti-spam).

Say that in the pitch. It reads as adult, not fake.
