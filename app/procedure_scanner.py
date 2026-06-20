"""Rule-based pre-scan: lists audit objectives and flags exceptions (no LLM)."""

import json
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")

with open(os.path.join(DATA_DIR, "transactions.json")) as f:
    TRANSACTIONS: list[dict] = json.load(f)

with open(os.path.join(DATA_DIR, "masters.json")) as f:
    MASTERS: dict = json.load(f)

AUTHORITY = {a["employee_id"]: a for a in MASTERS["approver_authority_matrix"]}
APPROVAL_THRESHOLD = 10_000

PROCEDURES = [
    {
        "id": "PROC-1",
        "objective": "Test operating effectiveness of PO approval authority controls",
        "assertion": "Authorization",
        "control_id": "CTRL-01",
        "account": "AP",
        "period": "2025-2026",
        "description": "Verify every PO >= $10,000 carries valid manual approval by someone with delegated authority.",
    },
    {
        "id": "PROC-2",
        "objective": "Test segregation of duties in the procure-to-pay cycle",
        "assertion": "Authorization",
        "control_id": "CTRL-02",
        "account": "AP",
        "period": "2025-2026",
        "description": "Confirm no single individual both requested and approved a purchase.",
    },
    {
        "id": "PROC-3",
        "objective": "Substantive test of AP — vouch payments to supporting documentation",
        "assertion": "Occurrence, Authorization",
        "control_id": "CTRL-03",
        "account": "AP",
        "period": "2025-2026",
        "description": "Vouch AP payments to PO/receipt; scan for duplicate invoices and missing support.",
    },
    {
        "id": "PROC-4",
        "objective": "Test journal entry review controls",
        "assertion": "Accuracy, Occurrence",
        "control_id": "CTRL-04",
        "account": "AP",
        "period": "2025-2026",
        "description": "Verify all items under CTRL-04 carry proper review. Expected: clean (zero deviations).",
    },
]


def _scan_ctrl01() -> list[str]:
    """PO approval authority: auto-approved above threshold + authority exceeded."""
    flags = []
    items = [t for t in TRANSACTIONS if t["control_id"] == "CTRL-01"]
    for t in items:
        if t["amount"] >= APPROVAL_THRESHOLD and t["approved_by"] == "SYSTEM":
            flags.append(f"{t['txn_id']}: auto-approved ${t['amount']:,.2f} (>= ${APPROVAL_THRESHOLD:,})")
        if t["approved_by"] in AUTHORITY:
            auth = AUTHORITY[t["approved_by"]]
            if t["amount"] > auth["max_approval_amount"]:
                flags.append(f"{t['txn_id']}: approver {t['approved_by']} max ${auth['max_approval_amount']:,.2f}, amount ${t['amount']:,.2f}")
    return flags


def _scan_ctrl02() -> list[str]:
    """Segregation of duties: requestor == approver."""
    flags = []
    items = [t for t in TRANSACTIONS if t["control_id"] == "CTRL-02"]
    for t in items:
        if t["requested_by"] == t["approved_by"] and t["approved_by"] != "SYSTEM":
            flags.append(f"{t['txn_id']}: requestor == approver ({t['requested_by']})")
    return flags


def _scan_ctrl03() -> list[str]:
    """Substantive AP: missing docs + duplicate invoices."""
    flags = []
    items = [t for t in TRANSACTIONS if t["control_id"] == "CTRL-03"]
    invoice_counts = Counter(t["invoice_number"] for t in TRANSACTIONS)

    for t in items:
        if t["supporting_doc"] is None:
            flags.append(f"{t['txn_id']}: missing supporting document")
        if invoice_counts[t["invoice_number"]] > 1:
            flags.append(f"{t['txn_id']}: invoice {t['invoice_number']} appears multiple times")

    # Also check for same vendor+amount+PO combos across all transactions
    for t in items:
        for other in TRANSACTIONS:
            if (
                other["txn_id"] != t["txn_id"]
                and other["vendor_id"] == t["vendor_id"]
                and other["amount"] == t["amount"]
                and other["supporting_doc"] == t["supporting_doc"]
                and t["supporting_doc"] is not None
            ):
                flag = f"{t['txn_id']}: possible duplicate of {other['txn_id']} (same vendor/amount/PO)"
                if flag not in flags:
                    flags.append(flag)
    return flags


def _scan_ctrl04() -> list[str]:
    """Journal entry review: should be clean."""
    flags = []
    items = [t for t in TRANSACTIONS if t["control_id"] == "CTRL-04"]
    for t in items:
        if t["deviations"]:
            flags.append(f"{t['txn_id']}: {t['deviations'][0]['type']}")
    return flags


SCANNERS = {
    "CTRL-01": _scan_ctrl01,
    "CTRL-02": _scan_ctrl02,
    "CTRL-03": _scan_ctrl03,
    "CTRL-04": _scan_ctrl04,
}


def get_procedures() -> list[dict]:
    """Return procedures with pre-scan flag counts."""
    results = []
    for proc in PROCEDURES:
        scanner = SCANNERS.get(proc["control_id"])
        flags = scanner() if scanner else []
        results.append({
            **proc,
            "pre_scan_flags": flags,
            "flag_count": len(flags),
        })
    return results


def get_procedure_by_id(proc_id: str) -> dict | None:
    for proc in PROCEDURES:
        if proc["id"] == proc_id:
            return proc
    return None
