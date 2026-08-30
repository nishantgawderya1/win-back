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
**NVIDIA Nemotron** (`nemotron-3-super-120b-a12b`), served through NVIDIA's
OpenAI-compatible API. Everywhere else is deterministic logic. If Nemotron is
unavailable, diagnosis falls back to rule-based classification, scored by how
much that fallback deserves to be trusted, and the pipeline continues.

Nemotron reasons before answering unless told not to. `LLM_ENABLE_THINKING`
controls it: off (the default) a diagnosis takes ~3.3s, on it takes ~10.4s and
the model's full chain is folded into the audit trail. Payments are diagnosed
concurrently (`BATCH_CONCURRENCY`), so a 75-record batch takes ~90s rather than
four minutes.

## What is real and what is simulated

Being precise about this, because it is the first thing worth checking:

| | |
|---|---|
| **Real** | Diagnosis (live Nemotron calls) |
| **Real** | Razorpay **payment links** — created through `/payment_links` in test mode, genuinely payable |
| **Real** | Webhook intake, HMAC-SHA256 signature verification, event de-duplication |
| **Real** | Recovery confirmation — `payment_link.paid` marks the payment recovered against the record the agent was chasing |
| Simulated | Card/UPI **retry** outcomes. Razorpay has no API that re-charges a failed payment; a failed authorization cannot be replayed, and genuinely recovering it needs fresh authorization from the customer, which is what the payment link is for |
| Simulated | SMS / WhatsApp / email delivery, and the inbound "promise to pay" reply |

Without credentials everything above degrades to simulation, so the demo runs
on a clean checkout.

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
curl -X POST http://localhost:8000/api/batch/upload -F "file=@data/sample_batch.csv"

# 6. (optional) Refresh the landing page's real demo figures from that run
python scripts/snapshot_demo_stats.py
```

Open <http://localhost:5173> for the landing page; the product lives at
`/dashboard` behind `/auth` and a three-step onboarding.

## Auth

Supabase email/password, off by default. A clean checkout runs with no
credentials in demo mode: any sign-in is accepted, the session is local, and
**the API answers anonymous callers** — which the sign-in screen states plainly
rather than implying a protection that is not there.

To enforce it:

1. Supabase → Settings → API. Copy the project URL and the anon/publishable key.
2. `frontend/.env` — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
3. Root `.env` — the same two values plus `AUTH_REQUIRED=true`.
4. Create a user in Supabase → Authentication → Users.

The project signs tokens with asymmetric keys (ES256), so the backend verifies
against the published JWKS and stores **no secret of its own**. Every route is
covered except two, both deliberate: `/api/health`, and the Razorpay webhook,
which authenticates by HMAC over the request body rather than a user token.

The live feed is covered too. A browser cannot set headers on a WebSocket
handshake, so `/ws/feed` takes the token as a query parameter — leaving it open
would have made the rest pointless, since it streams the same payment data.

## Database

SQLAlchemy 2.0 async ORM over SQLite by default — one gitignored `winback.db`,
no setup. Six tables: batch runs, payment records, audit log, halted actions,
promises to pay, and the saved stopping rules. The schema is created at startup,
and columns added to a model later are reconciled in place, because the project
carries no migration tool.

It runs on **Supabase / Postgres** unchanged — set `DATABASE_URL` to the asyncpg
form and the same startup path builds the schema there. Two things to know:

- **Percent-encode the password.** A literal `@` is read as the host separator,
  so a password like `p@ssw0rd` has to be written `p%40ssw0rd`.
- **`db.PROJECT.supabase.co` resolves IPv6-only.** On an IPv4-only network or
  host, use the session pooler and add `?prepared_statement_cache_size=0`, since
  pgbouncer cannot hold prepared statements across connections.

Measured on a 20-record batch: 30s against Supabase versus 25s against local
SQLite. The diagnosis call dominates each payment, so the extra network hops
cost less than the round trips suggest.

## Tests

```bash
make test        # pytest tests/ -v
```

## API surface

Every HTTP route is namespaced under `/api` so the React router can own the
bare product paths (`/batch`, `/audit`, `/halted`, `/settings`). The WebSocket
stays at `/ws/feed`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/webhook/razorpay` | Signature-verified webhook intake |
| POST | `/api/batch/upload` | Upload a CSV batch |
| GET | `/api/batch/{id}/status` | Poll progress |
| GET | `/api/batch/{id}/results` | Full results JSON |
| GET | `/api/batches` | All batch runs, newest first |
| GET | `/api/reports/{id}/summary` | Recovery metrics + breakdown |
| GET | `/api/reports/{id}/exceptions` | Unresolved payments for one batch |
| GET | `/api/exceptions` | Unresolved payments across batches |
| GET | `/api/audit` | Filterable audit search (agent, outcome, batch) |
| GET | `/api/audit/{payment_id}` | Audit trail for one payment |
| GET | `/api/audit/{batch_id}/export` | Download audit CSV |
| GET | `/api/payments/{payment_id}` | One payment's record + decision chain |
| GET | `/api/halted` | What the agent chose NOT to do |
| GET | `/api/halted/{batch_id}` | Same, scoped to one batch |
| GET | `/api/settings/rules` | Current stopping-rule thresholds |
| PUT | `/api/settings/rules` | Update them (persisted, live immediately) |
| GET | `/api/settings/connection` | Masked key id, webhook URL, model status |
| GET | `/api/promises/pending` | Promise-to-pay records due today |
| GET | `/api/demo/clock` | Agent clock + any demo offset |
| POST | `/api/demo/advance` | Fast-forward the agent, then run due retries |
| POST | `/api/demo/run-due` | Process due retries without moving the clock |
| POST | `/api/demo/reset` | Return to real time |
| WS | `/ws/feed` | Live agent-action stream |

## Screens

| Route | Screen |
|---|---|
| `/` | Landing page |
| `/auth` | Sign in (demo-only — no account is created) |
| `/onboarding/connect` · `/mode` · `/done` | Three-step first run |
| `/dashboard` | Live metrics, agent feed, batch progress |
| `/batch` · `/batch/{id}` | CSV upload · per-batch results |
| `/feed` | Full-screen agent action stream |
| `/audit` | Filterable audit trail + payment drill-down |
| `/halted` | Actions the agent declined to take |
| `/exceptions` | Everything that could not be recovered |
| `/settings` | Stopping rules, connection, channels |

## Stopping rules (non-negotiable, enforced in the planner)

- Max 3 retry attempts per payment
- 2-hour cooldown between outreach
- No outreach after the cutoff hour
- Payments above ₹50,000 require human approval

Defaults come from `.env`. A merchant can change any threshold on the Settings
screen; the value is persisted and applied to the very next payment without a
restart. `backend/config_runtime.py` holds the live values — `tools/rules.py`
and `tools/retry_timing.py` read from there, never from the frozen settings
singleton.

Every time-of-day rule is **merchant-local** (`MERCHANT_TIMEZONE`, default
`Asia/Kolkata`), not UTC. Quiet hours run from the cutoff hour until 9 AM local,
so a nudge cannot go out at 3 AM.

## The retry ladder

A retry is scheduled for the window that actually suits the failure — 9 AM
tomorrow for a UPI timeout, the 1st of next month for insufficient funds — which
is longer than one batch run. `backend/scheduler.py` is the worker that closes
that loop: it polls for payments whose window has arrived and re-enters the
graph at the planner (`resume_graph`), carrying the existing diagnosis rather
than paying for a second LLM call. Stopping rules run again on the way through,
so a resumed payment gets exactly the same guardrails as a fresh one.

Because those windows are real, they are also unwatchable in a demo. The demo
clock moves the agent's whole sense of time forward at once so scheduled retries
come due:

```bash
curl -X POST http://localhost:8000/api/demo/advance   -H 'Content-Type: application/json' -d '{"days": 1}'
```

Cooldowns, quiet hours and retry windows all shift together, and nothing
bypasses a stopping rule — advancing the clock changes *when* the agent
reconsiders a payment, never *whether* it may act.

## Diagnosis confidence

The planner will not spend a payment-network retry on a diagnosis it does not
trust (`MIN_CONFIDENCE_FOR_RETRY`); below the bar it downgrades to outreach,
which cannot fail expensively. The rule-based fallback therefore scores itself
by how reliable it actually is: a recognised Razorpay error code is a
deterministic lookup (0.7), while inferring a failure from the *absence* of a
code is a guess (0.45). A dead model no longer silently blocks every retry, and
`/api/settings/connection` reports whether the configured model is reachable.
