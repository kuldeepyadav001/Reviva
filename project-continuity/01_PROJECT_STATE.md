# Project state

**Updated:** 2026-08-27

## Git workflow
Side branch → pytest → push branch → merge `main` when tests pass.

## Current
All v1 services implemented. Tests: **34 passed**.

`main` after this commit includes:
- ingest HMAC+dedup+pipeline
- simulator labeled batch
- diagnosis rules then Ollama
- policy stopping rules
- executor audit + sim ₹
- React dashboard

Docker not run in this sandbox (no docker binary).

## Next for owner
`docker compose up --build` on a machine with Docker. Pull `llama3.2:1b`. Fill Razorpay test keys.
