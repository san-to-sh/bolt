"""Run all 4 procedures and save results to the demo cache.

Usage: python scripts/capture_demo_cache.py
Requires: ANTHROPIC_API_KEY in .env and chroma_data/ from ingest.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "workpapers", "demo_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

PROCEDURES = [
    {
        "objective": "Test operating effectiveness of PO approval authority controls",
        "assertion": "Authorization",
        "control_id": "CTRL-01",
        "account": "AP",
        "period": "2025-2026",
    },
    {
        "objective": "Test segregation of duties in the procure-to-pay cycle",
        "assertion": "Authorization",
        "control_id": "CTRL-02",
        "account": "AP",
        "period": "2025-2026",
    },
    {
        "objective": "Substantive test of AP — vouch payments to supporting documentation",
        "assertion": "Occurrence, Authorization",
        "control_id": "CTRL-03",
        "account": "AP",
        "period": "2025-2026",
    },
    {
        "objective": "Test journal entry review controls",
        "assertion": "Accuracy, Occurrence",
        "control_id": "CTRL-04",
        "account": "AP",
        "period": "2025-2026",
    },
]


async def main():
    from agent.graph import run_procedure

    for proc in PROCEDURES:
        ctrl = proc["control_id"]
        print(f"\nRunning {ctrl}...")

        state = await run_procedure(proc)
        wp = state.get("workpaper", {})
        trace = state.get("reasoning_trace", [])

        cache = {"workpaper": wp, "reasoning_trace": trace}

        path = os.path.join(CACHE_DIR, f"{ctrl}.json")
        with open(path, "w") as f:
            json.dump(wp, f, indent=2)

        print(f"  Saved to {path}")
        print(f"  Disposition: {wp.get('recommended_disposition', 'MISSING')}")
        print(f"  Exceptions: {len(wp.get('exceptions', []))}")

    print("\nDemo cache refreshed.")


if __name__ == "__main__":
    asyncio.run(main())
