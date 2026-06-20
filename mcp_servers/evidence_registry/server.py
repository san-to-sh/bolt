"""MCP server: master data and delegation-of-authority matrix."""

import json
import os
from mcp.server.fastmcp import FastMCP

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic")

with open(os.path.join(DATA_DIR, "masters.json")) as f:
    MASTERS: dict = json.load(f)

EMPLOYEES = {e["employee_id"]: e for e in MASTERS["employees"]}
VENDORS = {v["vendor_id"]: v for v in MASTERS["vendors"]}
AUTHORITY = {a["employee_id"]: a for a in MASTERS["approver_authority_matrix"]}

mcp = FastMCP("evidence_registry")


@mcp.tool()
def get_master_record(entity_id: str) -> str:
    """Return the full vendor or employee master record for a given ID."""
    if entity_id in EMPLOYEES:
        e = EMPLOYEES[entity_id]
        lines = [
            f"Employee Record: {entity_id}",
            f"  Name:       {e['name']}",
            f"  Role:       {e['role']}",
            f"  Department: {e['department']}",
            f"  Hire Date:  {e['hire_date']}",
        ]
        if entity_id in AUTHORITY:
            a = AUTHORITY[entity_id]
            lines.append(f"  Approver:   YES — max ${a['max_approval_amount']:,.2f}, categories: {', '.join(a['categories'])}")
        else:
            lines.append("  Approver:   NO — not in delegation-of-authority matrix")
        return "\n".join(lines)

    if entity_id in VENDORS:
        v = VENDORS[entity_id]
        related = ", ".join(v["related_entities"]) if v["related_entities"] else "(none)"
        lines = [
            f"Vendor Record: {entity_id}",
            f"  Name:            {v['name']}",
            f"  Status:          {v['status']}",
            f"  Category:        {v['category']}",
            f"  Onboarding Date: {v['onboarding_date']}",
            f"  Primary Approver:{v['primary_approver']}",
            f"  Related Entities:{related}",
        ]
        return "\n".join(lines)

    return f"Entity '{entity_id}' not found in employee or vendor master."


@mcp.tool()
def check_authority_matrix(approver: str, amount: float, category: str | None = None) -> str:
    """Check whether an approver holds delegated authority for a given amount and category."""
    if approver == "SYSTEM":
        return (
            f"Approver: SYSTEM (auto-approval)\n"
            f"  Amount: ${amount:,.2f}\n"
            f"  Result: SYSTEM is not a human approver. Amounts >= $10,000 require manual approval.\n"
            f"  Authority: N/A"
        )

    if approver not in AUTHORITY:
        return (
            f"Approver: {approver}\n"
            f"  Amount: ${amount:,.2f}\n"
            f"  Result: NOT AUTHORIZED — {approver} is not in the delegation-of-authority matrix."
        )

    auth = AUTHORITY[approver]
    within_amount = amount <= auth["max_approval_amount"]
    within_category = (
        "all" in auth["categories"]
        or category is None
        or category.lower() in [c.lower() for c in auth["categories"]]
    )
    authorized = within_amount and within_category

    status = "AUTHORIZED" if authorized else "NOT AUTHORIZED"
    reasons = []
    if not within_amount:
        reasons.append(f"amount ${amount:,.2f} exceeds max ${auth['max_approval_amount']:,.2f}")
    if not within_category:
        reasons.append(f"category '{category}' not in approved categories: {', '.join(auth['categories'])}")

    lines = [
        f"Approver: {approver} ({auth['name']}, {auth['role']})",
        f"  Amount:     ${amount:,.2f}",
        f"  Max Auth:   ${auth['max_approval_amount']:,.2f}",
        f"  Categories: {', '.join(auth['categories'])}",
        f"  Result:     {status}",
    ]
    if reasons:
        lines.append(f"  Reason:     {'; '.join(reasons)}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
