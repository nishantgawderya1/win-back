"""Write a small, deliberately-constructed batch for the demo.

synthetic_batch.py samples randomly, which is right for measuring behaviour but
wrong for a two-minute video: a random draw may contain no opt-out, no overdue
invoice, and nothing above the escalation threshold, leaving three screens empty
and the guardrails invisible.

Every row here exists to drive one path through the agent, and the file is sized
so a run finishes in roughly the length of a single demo shot.

    python data/demo_batch.py            -> data/demo_batch.csv
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone

# (label, error_code, hours_old, amount, prior_payments, prior_recoveries, opted_out)
#
# hours_old matters: detection separates an abandoned checkout from an overdue
# invoice by age, because neither carries a Razorpay error code.
ROWS = [
    ("UPI timeout, strong history -> retry, likely recovers",
     "BAD_REQUEST_PAYMENT_TIMED_OUT", 6, 2499.00, 9, 8, False),
    ("UPI timeout, weak history -> retry downgraded to outreach",
     "SERVER_ERROR_GATEWAY_TIMEOUT", 30, 1899.50, 6, 1, False),
    ("Insufficient funds, good payer -> retry on the 1st",
     "INSUFFICIENT_FUNDS", 14, 7450.00, 11, 7, False),
    ("Insufficient funds, thin history -> Hinglish SMS",
     "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS", 50, 3200.00, 2, 0, False),
    ("Hard bank block -> escalate, retrying cannot work",
     "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", 20, 12800.00, 5, 2, False),
    ("Abandoned checkout (no error code, hours old) -> payment link",
     "", 3, 4999.00, 3, 2, False),
    ("Overdue B2B invoice (no error code, 45 days old) -> email",
     "", 45 * 24, 88000.00, 4, 3, False),
    ("Subscription mandate failed -> renewal link",
     "SUBSCRIPTION_CHARGE_FAILED", 12, 899.00, 14, 9, False),
    ("Above the high-value threshold -> escalate for human approval",
     "BAD_REQUEST_PAYMENT_TIMED_OUT", 8, 74500.00, 7, 5, False),
    ("Customer replied STOP -> halted, never contacted again",
     "INSUFFICIENT_FUNDS", 26, 5600.00, 8, 4, True),
]

NAMES = ["Aarav", "Diya", "Rohan", "Ananya", "Kabir", "Meera", "Vivaan", "Isha",
         "Arjun", "Priya"]


def build(now: datetime) -> list[dict]:
    rows = []
    for i, (_label, code, hours, amount, prior, recovered, opted) in enumerate(ROWS):
        name = NAMES[i % len(NAMES)]
        rows.append(
            {
                # Stable ids: re-running the demo updates the same records
                # instead of scattering near-duplicates through the database.
                "payment_id": f"pay_demo{i + 1:02d}",
                "amount": f"{amount:.2f}",
                "customer_id": f"cust_demo{i + 1:02d}",
                "customer_name": name,
                "customer_phone": f"+9198{20000000 + i * 111111}",
                "customer_email": f"{name.lower()}@winback-demo.in",
                "razorpay_error_code": code,
                "prior_payments": prior,
                "prior_recoveries": recovered,
                "customer_opted_out": opted,
                "failed_at": (now - timedelta(hours=hours)).isoformat(),
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/demo_batch.csv")
    args = ap.parse_args()

    rows = build(datetime.now(timezone.utc))
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} records to {args.output}")
    for row, (label, *_rest) in zip(rows, ROWS):
        print(f"  {row['payment_id']}  {label}")


if __name__ == "__main__":
    main()
