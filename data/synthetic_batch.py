"""Generate a realistic batch of failed-payment records for the demo.

Usage:
    python data/synthetic_batch.py --count 75 --output data/sample_batch.csv
"""
from __future__ import annotations

import argparse
import csv
import random
import uuid
from datetime import datetime, timedelta

FAILURE_DISTRIBUTION = {
    "upi_timeout": 0.30,
    "card_insufficient": 0.25,
    "card_bank_block": 0.15,
    "checkout_abandoned": 0.15,
    "subscription_failed": 0.10,
    "invoice_overdue": 0.05,
}

ERROR_CODES = {
    "upi_timeout": ["BAD_REQUEST_PAYMENT_TIMED_OUT", "SERVER_ERROR_GATEWAY_TIMEOUT"],
    "card_insufficient": ["INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS"],
    "card_bank_block": [
        "BAD_REQUEST_PAYMENT_CARD_EXPIRED",
        "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
        "BAD_REQUEST_PAYMENT_FRAUD_DETECTED",
    ],
    "checkout_abandoned": [""],
    "subscription_failed": ["SUBSCRIPTION_CHARGE_FAILED"],
    "invoice_overdue": [""],
}

FIRST_NAMES = ["Aarav", "Diya", "Vivaan", "Ananya", "Rohan", "Isha", "Karan", "Meera",
               "Arjun", "Priya", "Kabir", "Sara", "Dev", "Nisha", "Rahul"]


def _weighted_types(count: int) -> list[str]:
    types, weights = zip(*FAILURE_DISTRIBUTION.items())
    return random.choices(types, weights=weights, k=count)


def generate(count: int) -> list[dict]:
    now = datetime.utcnow()
    rows = []
    for ftype in _weighted_types(count):
        prior = random.randint(0, 12)
        recovered = random.randint(0, min(prior, 8))
        failed_at = now - timedelta(hours=random.uniform(0, 72))
        name = random.choice(FIRST_NAMES)
        rows.append(
            {
                "payment_id": f"pay_{uuid.uuid4().hex[:12]}",
                "amount": round(random.uniform(299, 49999), 2),
                "customer_id": f"cust_{uuid.uuid4().hex[:8]}",
                "customer_name": name,
                "customer_phone": f"+9198{random.randint(10000000, 99999999)}",
                "customer_email": f"{name.lower()}{random.randint(1, 999)}@example.com",
                "razorpay_error_code": random.choice(ERROR_CODES[ftype]),
                "prior_payments": prior,
                "prior_recoveries": recovered,
                "customer_opted_out": random.random() < 0.05,
                "failed_at": failed_at.isoformat(),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=75)
    parser.add_argument("--output", type=str, default="data/sample_batch.csv")
    args = parser.parse_args()

    rows = generate(args.count)
    fieldnames = list(rows[0].keys())
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} records to {args.output}")


if __name__ == "__main__":
    main()
