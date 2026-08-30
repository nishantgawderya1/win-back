"""Capture a completed batch as the landing page's static stats snapshot.

The landing page must render without JavaScript and without a running backend,
so its numbers are baked in at build time rather than fetched. This script is
how they stay real: point it at a finished batch and it writes the figures the
marketing copy quotes.

    python scripts/snapshot_demo_stats.py                     # newest complete batch
    python scripts/snapshot_demo_stats.py --batch batch_abc123

Honesty note: `diagnosis_source` records whether the run's root causes actually
came from Nemotron or from the deterministic fallback. The landing page reads
it and labels the claim accordingly -- never assert AI reasoning a run did not
perform.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_API = "http://127.0.0.1:8000/api"
OUT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "data" / "demo-stats.json"


def fetch(api: str, path: str):
    with urllib.request.urlopen(f"{api}{path}", timeout=30) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--batch", default=None, help="batch id; default = newest complete")
    ap.add_argument("--output", default=str(OUT))
    args = ap.parse_args()

    try:
        batches = fetch(args.api, "/batches?limit=50")
    except (urllib.error.URLError, OSError) as exc:
        print(f"Could not reach {args.api} -- is the backend running? ({exc})")
        return 1

    if args.batch:
        chosen = next((b for b in batches if b["id"] == args.batch), None)
    else:
        complete = [b for b in batches if b["status"] == "complete" and b["total_records"] >= 10]
        chosen = max(complete, key=lambda b: b["total_records"], default=None)
    if chosen is None:
        print("No suitable completed batch found. Run one first: "
              "curl -X POST <api>/batch/upload -F 'file=@data/sample_batch.csv'")
        return 1

    bid = chosen["id"]
    results = fetch(args.api, f"/batch/{bid}/results")
    summary = fetch(args.api, f"/reports/{bid}/summary")
    exceptions = fetch(args.api, f"/exceptions?batch_id={bid}")
    audit = fetch(args.api, f"/audit?batch_id={bid}&limit=1000")

    records = results["records"]
    outcomes = collections.Counter(e["outcome"] for e in audit)
    nemotron_ok = outcomes.get("nemotron_ok", 0)
    fallback = outcomes.get("fallback_rules", 0)

    # Group the unresolved payments by the reason they could not be recovered.
    reasons = collections.Counter()
    for r in exceptions["records"]:
        if r["escalated"]:
            key = "escalated_to_human"
        elif r["halted"]:
            key = "stopping_rule_halted"
        else:
            key = "retried_without_success"
        reasons[key] += 1

    snapshot = {
        "batch_id": bid,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "record_count": len(records),
        "total_at_risk": round(summary["total_at_risk"], 2),
        "total_recovered": round(summary["total_recovered"], 2),
        "recovery_rate": round(summary["recovery_rate"], 4),
        "recovered_count": sum(1 for r in records if r["recovered"]),
        "escalated_count": sum(1 for r in records if r["escalated"]),
        "halted_count": sum(1 for r in records if r["halted"]),
        "unresolved_count": exceptions["count"],
        "total_unrecovered": round(exceptions["total_unrecovered"], 2),
        "failure_type_count": len(summary["by_failure_type"]),
        "by_failure_type": {
            k: {
                "count": v["count"],
                "at_risk": round(v["at_risk"], 2),
                "recovered": round(v["recovered"], 2),
            }
            for k, v in summary["by_failure_type"].items()
        },
        "exception_reasons": dict(reasons),
        "sample_exceptions": [
            {
                "payment_id": r["payment_id"],
                "amount": r["amount"],
                "failure_type": r["failure_type"],
                "reason": r["reason"],
            }
            for r in exceptions["records"][:3]
        ],
        # Which engine actually produced the root causes in this run.
        "diagnosis_source": "nemotron" if nemotron_ok > fallback else "rules_fallback",
        "diagnosis_counts": {"nemotron_ok": nemotron_ok, "fallback_rules": fallback},
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} from {bid}: "
          f"{snapshot['recovered_count']}/{snapshot['record_count']} recovered, "
          f"{snapshot['recovery_rate']:.1%}, diagnosis={snapshot['diagnosis_source']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
