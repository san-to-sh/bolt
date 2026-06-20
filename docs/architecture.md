# Bolt — System Architecture

> **The auditor reaches the opinion. Bolt does the legwork to get them there.**

## 1. Design Philosophy

Bolt is an AI audit agent that autonomously executes audit procedures and drafts
structured workpapers for human sign-off. It demonstrates **continuous controls testing
with a human-in-the-loop**: the agent runs each procedure across the full population in
seconds; the auditor exercises professional judgment on the exceptions.

The system enforces a strict separation between evidence-gathering (automated) and
opinion-forming (human). Bolt never issues a final audit opinion — it describes findings,
cites criteria, and hands the judgment call to the auditor.

**Core invariant:** every conclusion in a workpaper traces to a criterion returned by the
criteria RAG layer. No conclusion without a cited criterion.

## 2. Agent Topology

Bolt uses a ReAct-style loop implemented as a LangGraph StateGraph:

```
RECEIVE PROCEDURE (objective + control_id + assertion + population scope)
    │
    ▼
┌─────────┐
│  PLAN   │  Which population? Which criteria? What constitutes a deviation?
└────┬────┘
     │
     ▼
┌─────────┐     ┌──────────────────────────┐
│   ACT   │────▶│  Sufficiency check       │
│ (tools) │◀────│  (hard cap: 3 rounds)    │
└────┬────┘     └──────────────────────────┘
     │ sufficient
     ▼
┌─────────────┐
│ SYNTHESIZE  │  Cross-ref deviations × criteria × precedent
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  WORKPAPER  │  Structured JSON → validate disposition suffix
└──────┬──────┘
       │
       ▼
 [AUDITOR SIGNS OFF]
```

### State Management

`AgentState` is a TypedDict with annotated reducers:

| Field             | Type            | Reducer           | Purpose                                    |
|-------------------|-----------------|-------------------|--------------------------------------------|
| `procedure`       | `dict`          | —                 | Objective, assertion, control_id, account   |
| `plan`            | `str`           | —                 | Natural-language audit plan                 |
| `tool_calls`      | `list[dict]`    | `operator.add`    | Accumulated tool invocations                |
| `evidence`        | `dict`          | `merge_evidence`  | Deduplicated evidence from tool results     |
| `reasoning_trace` | `list[str]`     | `operator.add`    | Streaming trace for the UI                  |
| `workpaper`       | `dict`          | —                 | Final structured output                     |
| `act_count`       | `int`           | —                 | Loop iteration counter (max 3)              |

The `merge_evidence` reducer accumulates lists with deduplication and deep-merges nested
dicts, preventing duplicate tool results across act rounds.

## 3. Tool Layer (MCP Servers)

Bolt communicates with four MCP servers over stdio. Each server is an independent process
launched by the `MCPManager` async context manager.

```
┌────────────────────────────────────────────────────────┐
│                    LangGraph Agent                      │
│                   (Claude Sonnet)                       │
└──────┬─────────┬──────────┬──────────┬─────────────────┘
       │ stdio   │ stdio    │ stdio    │ stdio
       ▼         ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ledger_db │ │evidence_ │ │criteria_ │ │workpaper_rag │
│          │ │registry  │ │rag  ★    │ │              │
│get_pop.. │ │get_master│ │query_    │ │query_prior_  │
│test_it.. │ │check_    │ │criteria  │ │workpapers    │
│sample_.. │ │authority │ │          │ │              │
└──────────┘ └──────────┘ └──────────┘ └──────────────┘
     │              │           │              │
     ▼              ▼           ▼              ▼
 transactions   masters.json  ChromaDB      ChromaDB
    .json                    "criteria"   "prior_workpapers"
```

★ **criteria_rag is the critical grounding tool.** Every workpaper conclusion must cite a
criterion returned by this server. It searches across two corpora:

- **Internal policies** (4 documents, 28 chunks): PO approval, segregation of duties,
  vendor onboarding, journal entry review.
- **Synthetic audit standards** (3 documents, 15 chunks): control operating-effectiveness
  testing, financial-statement assertions, audit evidence and sampling. Written in
  original language — no verbatim text from published standards.

Each chunk carries metadata: `source`, `section`, `doc_type` (policy | standard), and
for standards an `assertion` or `objective` tag enabling precise citation.

## 4. Workpaper Output Schema

Bolt always produces this structure. The agent never issues an opinion — it drafts for
sign-off.

| Field                     | Type         | Constraint                                         |
|---------------------------|--------------|-----------------------------------------------------|
| `objective`               | string       | What this procedure tests                           |
| `assertion`               | string       | e.g. Authorization, Occurrence, Completeness        |
| `control_id`              | string       | CTRL-01 through CTRL-04                             |
| `procedure_performed`     | string       | What Bolt actually did, in audit language            |
| `population_summary`      | string       | Source, period, size, total value                    |
| `sample`                  | string       | Items selected + method, or "full population"       |
| `exceptions`              | list[string] | Item ref + deviation + criterion breached            |
| `deviation_rate`          | string       | e.g. "2 of 9 items (22.2%)"                        |
| `criteria_cited`          | list[string] | Policy/standard source + section + clause            |
| `prior_year_reference`    | list[string] | Prior WP ref + conclusion + recurrence note          |
| `preliminary_conclusion`  | string       | **Never a final opinion** — describes findings       |
| `judgment_note`           | string       | What the auditor must decide that Bolt cannot        |
| `recommended_disposition` | string       | Must end with **"— Auditor judgment required"**     |
| `prepared_at`             | string       | ISO timestamp                                        |

### Disposition Enforcement

`recommended_disposition` must always end with "— Auditor judgment required". This is
enforced in the workpaper prompt AND validated in `workpaper_node` — if the LLM omits
the suffix, the node appends it before returning.

## 5. UI Architecture

Three-column Streamlit layout (dark theme for projector demos):

| Left Panel              | Center Panel            | Right Panel             |
|------------------------|-------------------------|-------------------------|
| Procedure picker       | Live reasoning trace    | Workpaper card          |
| Pre-scan flag badges   | [PLAN] / [ACT] / etc.  | Disposition badge       |
| Custom procedure form  | Streamed via st.status  | Exceptions + criteria   |
| Demo mode toggle       |                         | PDF download button     |

### Demo Mode

A sidebar toggle (or `BOLT_DEMO_MODE=true` env var) loads pre-cached workpapers from
`output/workpapers/demo_cache/` instead of calling the API. This ensures the demo
survives an API outage on stage. The cache can be refreshed via
`scripts/capture_demo_cache.py`.

## 6. Data Pipeline

```
data/policies/*.md  ─┐                    ┌─► criteria_rag server
data/standards/*.md ─┤── ingest.py ──────►│   (ChromaDB "criteria")
                     │   (chunk by ##)    │
data/synthetic/      │                    │
  prior_workpapers  ─┘── ingest.py ──────►└─► workpaper_rag server
    .json                (one doc/wp)         (ChromaDB "prior_workpapers")

data/synthetic/
  transactions.json ──────────────────────►   ledger_db server
  masters.json     ──────────────────────►   evidence_registry server
```

### Embedding Strategy

ChromaDB's default embedding model (all-MiniLM-L6-v2) is used for both collections.
Policies are chunked at `##` section boundaries to preserve clause-level granularity.
Standards are chunked at `##` boundaries with additional `assertion` and `objective`
metadata tags detected via keyword matching, enabling filtered retrieval by assertion
type.

## 7. Reliability

- **Tenacity retry** on Anthropic 529 (overloaded) errors: exponential backoff, 3 attempts.
- **JSON parse fallback** in `workpaper_node`: if the LLM output is not valid JSON, a
  structured fallback workpaper is generated with the raw output preserved.
- **Canned fallback**: demo mode with cached results for all 4 procedures.
- **Deterministic data**: planted deviations make each procedure reproducible on stage.

## 8. Conference Context

- **Venue:** University of Duisburg-Essen, Sept 2–4, 2026.
- **Track:** Continuous auditing, in collaboration with Rutgers CARLAB / WCARS.
- **Audience:** Internal-audit academics and practitioners.
- **Frame:** Continuous controls testing with a human-in-the-loop. The agent runs the
  procedure across the full population in seconds; the auditor exercises judgment on the
  exceptions. Adaptation, not replacement.
