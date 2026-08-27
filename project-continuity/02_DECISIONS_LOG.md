# Decisions log

| Date | Decision | Why | State |
|---|---|---|---|
| 2026-08-27 | Delete prior monolith implementation | Owner rejected architecture change and unstaged build | Clean workspace |
| 2026-08-27 | Solo Elite: phase-gated, confirm each phase | Owner instruction | Active |
| 2026-08-27 | Keep 6 FastAPI services | Owner research + Serina/SafeRide pattern; confirmed | Locked |
| 2026-08-27 | Ollama as Compose service | Owner confirmed | Locked |
| 2026-08-27 | Internship duration 6 months, in-person | Owner confirmed (overrides master prompt “12 months”) | Form lock |
| 2026-08-27 | Maintain `project-continuity/` from day zero | Owner mandatory | This folder |
| 2026-08-27 | Phase 2 research accepted | Owner: “yess next” | Phase 3 |
| 2026-08-27 | Shared package + sync HTTP + nginx edge (A–C) | Recommended in P2; owner said next without objecting | Treat as default in Phase 4 unless reversed |
| 2026-08-27 | Ollama small model (1b/3b) | P2 suggestion D; not explicitly named | Confirm in Phase 4 |
| 2026-08-27 | Owner napping: continue without per-phase chat | “keep on moving… u start work” | Phases 4–5 locked; Stage 1 executed only |
| 2026-08-27 | Stage 1 = health skeleton only | Do not dump remaining stages | Stop after Stage 1 |
| 2026-08-27 | Sandbox has no `docker` | Cannot compose-up here | Files ready, runtime unverified |
| 2026-08-27 | Frontend is React (Vite), nginx serves `dashboard/dist` | Owner: use React | Stage 1 dashboard replaced |
| 2026-08-27 | Tests every stage (pytest) | Owner | 7 tests passing HMAC/dedup/ingest |
| 2026-08-27 | SSH ed25519 deploy key `id_ed25519_reviva` | Owner will create GitHub repo | Waiting for repo URL + deploy key added |
