# Planted Deviation Scenarios

All deviations are deterministic so the demo produces reproducible results.

## PROC-1 — PO Approval Authority (CTRL-01)

Tests that every PO >= $10,000 carries valid manual approval by an authorized approver.

| Txn | Amount | Deviation | Detail |
|-----|--------|-----------|--------|
| TXN-004 | $12,500 | `auto_approved_above_threshold` | approved_by = SYSTEM; amount exceeds $10k threshold requiring manual approval |
| TXN-003 | $45,000 | `approval_authority_exceeded` | Approved by E-302 (Thomas Nguyen, max $25,000); amount exceeds his authority |

**Expected result:** 2 deviations out of 6 CTRL-01 items >= $10k. DEFICIENCY NOTED.
**Prior year:** WP-2024-001 noted auto-approval bypass (recurring); WP-2024-006 found no authority-limit breaches (new finding this year).

## PROC-2 — Segregation of Duties (CTRL-02)

Tests that no single individual both requests and approves a purchase.

| Txn | Amount | Deviation | Detail |
|-----|--------|-----------|--------|
| TXN-011 | $4,200 | `segregation_of_duties` | requested_by = E-211, approved_by = E-211 (Robert Haines approved his own request) |

**Expected result:** 1 deviation out of 6 CTRL-02 items. DEFICIENCY NOTED.
**Prior year:** WP-2024-002 had zero SoD violations — this is a new finding.

## PROC-3 — Substantive AP Test (CTRL-03)

Vouch AP payments to supporting documentation; scan for duplicate invoices.

| Txn | Amount | Deviation | Detail |
|-----|--------|-----------|--------|
| TXN-016 | $14,200 | `missing_supporting_doc` | supporting_doc = null; no PO or receipt on file |
| TXN-019 | $45,000 | `duplicate_invoice` | Same vendor (V-103), same amount, same PO ref as TXN-003; possible duplicate payment |

**Expected result:** 2 deviations out of 5 CTRL-03 items. DEFICIENCY NOTED / ESCALATE.
**Prior year:** WP-2024-003 noted missing receiving reports (recurring pattern); WP-2024-007 found no duplicates (new finding this year).

## PROC-4 — Clean Control: Journal Entry Review (CTRL-04)

Tests that all items under CTRL-04 pass with zero deviations.

| Txn | Amount | Deviation | Detail |
|-----|--------|-----------|--------|
| *(none)* | — | — | All 5 CTRL-04 items have empty deviation arrays |

**Expected result:** 0 deviations. NO EXCEPTION.
**Prior year:** WP-2024-004 also found no deviations — consistent clean result.
