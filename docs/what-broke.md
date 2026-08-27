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
