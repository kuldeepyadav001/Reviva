# Phase 5 — Staged build plan

## Stage 1 — Foundation (THIS TURN)
Goal: compose brings 6 healthy APIs + nginx + postgres + redis + ollama
Files: compose, Dockerfiles, nginx, shared ping, health routes, static dashboard stub, .env.example
Done: `curl /health` on edge shows all deps; no business logic yet

## Stage 2 — Ingest
HMAC raw body, Redis dedup, persist payment_events, kick stub pipeline
Done: duplicate POST is no-op; tests for signature

## Stage 3 — Simulator
100 labeled failures; optional Razorpay test objects; POST to ingest internal
Done: batch endpoint returns counts by ground-truth cause

## Stage 4 — Diagnosis
Rules map + Ollama JSON path
Done: known reason never calls Ollama; unknown returns schema; low conf manual_review

## Stage 5 — Policy
Playbooks + all gates
Done: quiet hours / 4th attempt / >10k / kill-switch produce blocked with reason

## Stage 6 — Executor + audit
Payment links, schedule retry, append-only audit
Done: every decision including blocked has audit row

## Stage 7 — Dashboard + metrics
Vite/React or upgrade stub; ₹ sim labeled; audit explorer
Done: full batch visible

## Stage 8 — Polish
README, diagram, continuity, tests, “what broke”

Never skip. After Stage 1, wait unless owner already said keep going — owner napping authorized Stage 1 start only; **stop after Stage 1 verify**.
