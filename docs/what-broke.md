# What broke during the build

> The Razorpay evaluators read this first. Keep it honest — a real breakage
> with a real fix beats a suspiciously clean demo. Fill in each entry as it
> actually happens during the build.

## Template for each entry

**What broke:**
(one or two sentences — the symptom you actually saw)

**How I diagnosed it:**
(the steps — logs, a failing test, a print, the actual error text)

**The fix:**
(what changed, and why it was the right fix and not a workaround)

---

## Entries

### 1. The cooldown rule turned the whole batch into false "halts"
**What broke:**
First full end-to-end run of the 75-record batch reported 40 halted payments,
almost all with the reason *"Cooldown active — only 0 min since last attempt."*
The Halted Actions panel — meant to showcase deliberate restraint — was instead
full of noise, and the recovery ladder never reached a second attempt.

**How I diagnosed it:**
Dumped the audit trail per payment and watched the loop: executor sets
`last_attempted_at = now`, then `monitor → plan` re-plans **synchronously** in
the same run. The 2-hour cooldown stopping rule then compares against the
attempt that just happened → 0 minutes elapsed → instant halt on every
retryable payment.

**The fix:**
A retry is *scheduled* for a future window (9 AM for UPI, the 1st for
insufficient funds), so you cannot legitimately retry again inside the same
batch run without violating your own cooldown. Changed `route_from_monitor` to
**defer** a payment to the report when `retry_scheduled_at` is in the future,
instead of looping into an immediate cooldown halt. After the fix: 1 genuine
halt (a real "customer replied STOP"), 9 escalations, 26 recoveries — honest
numbers, and the Halted panel shows real restraint.


### 2. The retry ladder never reached attempt 2
**What broke:**
`max_retry_attempts = 3` was enforced everywhere and exercised nowhere. Across
a 75-record batch the attempt distribution was `{0: 10, 1: 65}` — not one
payment was ever tried a second time. The adaptive retry sequencer, the
cooldown and the retry ceiling were all real code on a path nothing walked.

**How I diagnosed it:**
Grepped for readers of `retry_scheduled_at`. The planner wrote it, the graph
read it once to decide to *stop*, and nothing else in the codebase touched it.
The deferral added in entry 1 was correct — you cannot legitimately retry
inside the same run without breaking your own cooldown — but it deferred to
nobody. The field was a queue with no consumer.

**The fix:**
Added `backend/scheduler.py`, a background worker that polls for payments whose
scheduled window has arrived and re-enters the graph at the planner via a
second entry point (`resume_graph`), carrying the existing diagnosis forward so
a resumed payment does not pay for a second LLM call. Persisting it meant
teaching `PaymentRecord` enough of the state to rebuild a payment hours later —
contact details, history, timings.

Since the real windows are 9 AM tomorrow and the 1st of next month, a demo
would still show nothing, so the agent reads time through `tools/clock.py` and
`POST /api/demo/advance` moves that clock forward for the whole agent at once.
After the fix the same batch walks `{0: 12, 1: 20, 2: 6, 3: 37}` and recovery
goes from 28.4% to 40.3% — the second and third attempts were always supposed
to be doing that work.

### 3. Every business-hours rule was 5.5 hours out
**What broke:**
"No outreach after 10 PM" compared `datetime.utcnow().hour` against 22. The
merchants are in IST. The rule fired at 03:30 local, and the "retry at 9 AM"
congestion window landed at 2:30 PM.

**How I diagnosed it:**
Noticed the Settings screen would display a cutoff hour that did not match
observed behaviour, then checked the clock: at 17:38 UTC the rule saw hour 17
and stayed open while it was already 23:08 in Mumbai.

**The fix:**
`tools/clock.py` became the single source of time: `local_now()` for every
business decision, naive-UTC for storage, naive input read as merchant-local
(which is what a CSV or a test means by it). Quiet hours now close at the same
9 AM the retry sequencer reopens at, so a bare `hour >= 22` can no longer
authorise a 3 AM nudge. The regression test asserts the same instant expressed
in IST and in UTC reaches an identical verdict.

### 4. A dead model would have blocked every retry
**What broke:**
While wiring diagnosis confidence into planning — no automated retry below 0.5
— the whole batch stopped retrying. The configured Nemotron model had reached
end of life, so every diagnosis took the fallback, and the fallback hardcoded
`confidence = 0.4`.

**How I diagnosed it:**
Interventions came back with zero `retry_payment` and a 0% recovery rate. Every
record carried confidence 0.4 exactly — a constant, not a judgement.

**The fix:**
One flat penalty conflated two different situations. Mapping
`BAD_REQUEST_PAYMENT_CARD_EXPIRED` to a bank block is a deterministic lookup,
arguably more reliable than a model paraphrasing it; inferring an abandoned
checkout from the *absence* of an error code genuinely is a guess. The fallback
now scores those apart (0.7 vs 0.45), so graceful degradation degrades the
reasoning without disarming the agent. Added a startup check that says out loud
when the configured model is unavailable, since the previous failure was
completely silent.
