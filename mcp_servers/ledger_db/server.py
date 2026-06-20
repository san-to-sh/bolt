"""MCP server: population retrieval, control testing, and sampling."""

import json
import math
import os
import random
from collections import Counter
from mcp.server.fastmcp import FastMCP

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic")

with open(os.path.join(DATA_DIR, "transactions.json")) as f:
    TRANSACTIONS: list[dict] = json.load(f)

with open(os.path.join(DATA_DIR, "masters.json")) as f:
    MASTERS: dict = json.load(f)

AUTHORITY = {row["employee_id"]: row for row in MASTERS["approver_authority_matrix"]}

mcp = FastMCP("ledger_db")

APPROVAL_THRESHOLD = 10_000


@mcp.tool()
def get_population(account: str = "AP", period: str = "2025-2026", control_id: str | None = None) -> str:
    """Return the in-scope population of items, optionally filtered by control_id."""
    items = TRANSACTIONS
    if control_id:
        items = [t for t in items if t["control_id"] == control_id]

    if not items:
        return f"No items found for account={account}, period={period}, control_id={control_id}"

    total_value = sum(t["amount"] for t in items)
    lines = [
        f"Population: account={account}, period={period}, control_id={control_id or 'all'}",
        f"Items: {len(items)}  |  Total value: ${total_value:,.2f}",
        "-" * 80,
    ]
    for t in items:
        doc = t["supporting_doc"] or "(none)"
        lines.append(
            f"  {t['txn_id']}  {t['vendor_name']:<30s}  {t['invoice_number']:<18s}  "
            f"${t['amount']:>10,.2f}  {t['date']}  doc={doc}"
        )
    return "\n".join(lines)


@mcp.tool()
def test_items_against_control(control_id: str, vendor_id: str | None = None) -> str:
    """Run the deviation test for a control over the population.

    Checks: planted deviations, approval-authority limits, SoD (requestor==approver),
    missing supporting docs, and duplicate invoice numbers.
    Returns a deviation list and deviation rate.
    """
    items = [t for t in TRANSACTIONS if t["control_id"] == control_id]
    if vendor_id:
        items = [t for t in items if t["vendor_id"] == vendor_id]

    if not items:
        return f"No items found for control_id={control_id}, vendor_id={vendor_id}"

    deviations: list[str] = []
    invoice_counts: Counter[str] = Counter(t["invoice_number"] for t in items)

    for t in items:
        txn = t["txn_id"]

        for planted in t.get("deviations", []):
            deviations.append(f"{txn}: [{planted['type']}] {planted['detail']}")
            continue

        if len(t.get("deviations", [])) > 0:
            continue

        if t["amount"] >= APPROVAL_THRESHOLD and t["approved_by"] == "SYSTEM":
            deviations.append(
                f"{txn}: [auto_approved_above_threshold] "
                f"${t['amount']:,.2f} auto-approved; requires manual approval >= ${APPROVAL_THRESHOLD:,}"
            )

        if t["approved_by"] in AUTHORITY:
            auth = AUTHORITY[t["approved_by"]]
            if t["amount"] > auth["max_approval_amount"]:
                deviations.append(
                    f"{txn}: [approval_authority_exceeded] "
                    f"Approver {t['approved_by']} ({auth['name']}) max ${auth['max_approval_amount']:,.2f}; "
                    f"amount ${t['amount']:,.2f}"
                )

        if t["requested_by"] == t["approved_by"] and t["approved_by"] != "SYSTEM":
            deviations.append(
                f"{txn}: [segregation_of_duties] "
                f"Requestor and approver are the same person ({t['requested_by']})"
            )

        if t["supporting_doc"] is None:
            deviations.append(
                f"{txn}: [missing_supporting_doc] "
                f"No supporting document on file for ${t['amount']:,.2f}"
            )

        if invoice_counts[t["invoice_number"]] > 1:
            dupes = [
                other["txn_id"]
                for other in items
                if other["invoice_number"] == t["invoice_number"] and other["txn_id"] != txn
            ]
            if dupes:
                deviations.append(
                    f"{txn}: [duplicate_invoice] "
                    f"Invoice {t['invoice_number']} also appears in {', '.join(dupes)}"
                )

    seen = set()
    unique_deviations = []
    for d in deviations:
        key = d.split(":")[0] + d.split("]")[0]
        if key not in seen:
            seen.add(key)
            unique_deviations.append(d)

    n = len(items)
    d = len(unique_deviations)
    rate = f"{d} of {n} items ({d/n*100:.1f}%)" if n else "N/A"

    lines = [
        f"Control test: {control_id}",
        f"Population tested: {n} items",
        f"Deviations found: {d}",
        f"Deviation rate: {rate}",
        "-" * 80,
    ]
    if unique_deviations:
        lines.append("DEVIATIONS:")
        for dev in unique_deviations:
            lines.append(f"  • {dev}")
    else:
        lines.append("NO DEVIATIONS — control operating effectively for tested population.")

    return "\n".join(lines)


@mcp.tool()
def sample_population(
    account: str = "AP",
    period: str = "2025-2026",
    method: str = "random",
    sample_size: int = 10,
    control_id: str | None = None,
) -> str:
    """Select a deterministic attribute sample from the population.

    method: 'random' (seeded) or 'monetary_unit'.
    Returns the selected item IDs.
    """
    items = TRANSACTIONS
    if control_id:
        items = [t for t in items if t["control_id"] == control_id]

    if not items:
        return f"No items found for account={account}, period={period}"

    sample_size = min(sample_size, len(items))

    if method == "monetary_unit":
        total = sum(t["amount"] for t in items)
        interval = total / sample_size
        rng = random.Random(42)
        start = rng.uniform(0, interval)
        cumulative = 0.0
        selected = []
        pointer_idx = 0
        pointers = [start + i * interval for i in range(sample_size)]

        for t in items:
            cumulative += t["amount"]
            while pointer_idx < len(pointers) and pointers[pointer_idx] <= cumulative:
                if t["txn_id"] not in [s["txn_id"] for s in selected]:
                    selected.append(t)
                pointer_idx += 1
    else:
        rng = random.Random(42)
        selected = rng.sample(items, sample_size)

    total_selected = sum(t["amount"] for t in selected)
    lines = [
        f"Sample: method={method}, size={len(selected)}, account={account}, period={period}",
        f"Total sample value: ${total_selected:,.2f}",
        "-" * 80,
    ]
    for t in selected:
        lines.append(
            f"  {t['txn_id']}  {t['vendor_name']:<30s}  ${t['amount']:>10,.2f}  {t['date']}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
