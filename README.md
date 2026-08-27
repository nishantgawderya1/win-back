# WinBack AI

Autonomous, multi-agent **revenue recovery** for Razorpay merchants.
Built for the Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery.

WinBack ingests failed payments (webhook or batch CSV), runs them through a
bounded **LangGraph** pipeline that diagnoses the root cause, chooses the right
recovery action, enforces hard stopping rules, and reports exactly how much
money was recovered — with a full audit trail of every decision, **including
the decisions to do nothing.**

## LLM: NVIDIA Nemotron

AI judgment is used in exactly one place — the **diagnosis** node — via
**NVIDIA Nemotron**, served through NVIDIA's OpenAI-compatible API
(`https://integrate.api.nvidia.com/v1`). Everywhere else is deterministic
logic. If Nemotron is unavailable, diagnosis falls back to rule-based
classification with a lower confidence score and the pipeline continues.

Get a key at [build.nvidia.com](https://build.nvidia.com) → pick a Nemotron
model → **Get API Key**.

## Architecture

```
Input (webhook / batch CSV)
  → detect     classify failure type + urgency        (rules, no LLM)
  → diagnose   root cause + recovery score            (Nemotron — the one LLM call)
  → plan       stopping rules → escalation → action   (deterministic)
  → execute    retry / link / SMS / WhatsApp / email  (idempotency keys)
  → monitor    check outcome, loop back or finish
  → report     batch metrics + exception list + audit CSV
     ├─ halt      (a stopping rule fired)
     └─ escalate  (an escalation threshold crossed)
```

Every node logs before and after via `log_action()`, which both persists an
audit row and broadcasts a live event over `/ws/feed`.

## Project layout

```
backend/
  agents/     detection, diagnosis, planner, executor, monitor, reporter, nodes(halt/escalate)
  graph/      state.py (WinBackState contract) + graph.py (StateGraph)
  tools/      llm.py (Nemotron), razorpay, comms, audit, rules, retry_timing
  api/        main.py, ws_manager.py, routes/(webhook, batch, reports)
  db/         models, session, repository
  runner.py   batch orchestration over the graph
  config.py   all env vars, typed (pydantic-settings)
frontend/     React 18 + Vite 5 + Recharts
data/         synthetic_batch.py generator
tests/        rules, detection, retry-timing
docs/         what-broke.md
```

## Run it locally

```bash
# 1. Backend deps + env
cd backend && pip install -r requirements.txt --break-system-packages && cd ..
cp .env.example .env          # fill in NVIDIA_API_KEY + Razorpay test keys

# 2. Generate demo data
make seed                     # -> data/sample_batch.csv (75 records)

# 3. Start backend
make backend                  # uvicorn on :8000

# 4. Start frontend (separate terminal)
make frontend                 # vite on :5173

# 5. Upload a batch
curl -X POST http://localhost:8000/batch/upload -F "file=@data/sample_batch.csv"
```

## Tests

```bash
make test        # pytest tests/ -v
```

## API surface

| Method | Path | Purpose |
|---|---|---|
| POST | `/webhook/razorpay` | Signature-verified webhook intake |
| POST | `/batch/upload` | Upload a CSV batch |
| GET | `/batch/{id}/status` | Poll progress |
| GET | `/batch/{id}/results` | Full results JSON |
| GET | `/reports/{id}/summary` | Recovery metrics + breakdown |
| GET | `/reports/{id}/exceptions` | Unresolved payments + reasons |
| GET | `/audit/{payment_id}` | Audit trail for one payment |
| GET | `/audit/{batch_id}/export` | Download audit CSV |
| GET | `/halted/{batch_id}` | What the agent chose NOT to do |
| GET | `/promises/pending` | Promise-to-pay records due today |
| WS | `/ws/feed` | Live agent-action stream |

## Stopping rules (non-negotiable, enforced in the planner)

- Max 3 retry attempts per payment
- 2-hour cooldown between outreach
- No outreach after 10 PM
- Payments above ₹50,000 require human approval
