# Bolt — AI Audit Assistant Agent

> The auditor reaches the opinion. Bolt does the legwork to get them there.
> Bolt gathers and tests the evidence. Bolt never signs the workpaper.

---

## Project Purpose

A live demo / research artifact for the **3rd International Conference on Auditing and
Artificial Intelligence** (University of Duisburg-Essen, Sept 2–4 2026).

Bolt is an AI audit agent. An auditor selects an **audit procedure** — a control test
or a substantive test tied to an objective and assertion. Bolt autonomously pulls the
relevant population, tests items against the control criteria, retrieves the governing
policy and audit standard, finds prior-year workpapers as precedent, and drafts a
structured **audit workpaper** for the auditor to review and sign off.

**Core thesis:** The AI does the legwork. The human reaches the opinion.
This mirrors the conference's recurring theme — the challenge is *adaptation, not
replacement*. Bolt is the "staff auditor" doing fieldwork; the human is the
engagement lead who exercises professional judgment.

> Bolt is a spinoff of **Balto** (an AI fraud-investigation agent). Same tech stack and
> agent topology, re-pointed from fraud alerts to audit procedures. If something here is
> ambiguous, the Balto architecture is the reference implementation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Claude Sonnet (Anthropic) via `langchain-anthropic` |
| Agent Framework | LangGraph (StateGraph, ReAct loop) |
| Tool Integration | MCP (Model Context Protocol) over stdio |
| RAG | ChromaDB (persistent, local embeddings) |
| UI | Streamlit (3-column, dark theme) |
| Data | Synthetic JSON + Markdown criteria docs (no real PII, no verbatim standards) |
| Language | Python 3.11+ |

---

## Project Structure

```
bolt/
├── CLAUDE.md                   # You are here
├── .env                        # ANTHROPIC_API_KEY — never commit
├── .gitignore
├── requirements.txt
├── README.md
│
├── app/
│   ├── streamlit_app.py        # Main UI — procedure picker + live trace + workpaper
│   └── procedure_scanner.py    # Rule-based pre-scan: lists audit objectives + flags exceptions (no LLM)
│
├── agent/
│   ├── graph.py                # LangGraph definition (plan → act → synthesize → workpaper)
│   ├── nodes.py                # Node functions + MCPManager
│   ├── state.py                # AgentState TypedDict + custom reducers
│   └── prompts.py              # System + node prompts
│
├── mcp_servers/
│   ├── ledger_db/              # Population retrieval + control testing + sampling
│   │   └── server.py
│   ├── evidence_registry/      # Master data + delegation-of-authority matrix
│   │   └── server.py
│   ├── criteria_rag/           # *** CRITICAL *** control policies + audit standards (RAG)
│   │   └── server.py
│   └── workpaper_rag/          # Prior-year workpapers / findings for precedent (RAG)
│       └── server.py
│
├── data/
│   ├── synthetic/
│   │   ├── transactions.json   # The population under audit (mix of compliant + exceptions)
│   │   ├── masters.json        # Vendor/employee master + approver authority matrix
│   │   └── prior_workpapers.json  # Prior-year audit findings + dispositions
│   ├── policies/               # Internal control policies (Markdown)
│   └── standards/              # PARAPHRASED / SYNTHETIC audit-standard summaries (Markdown)
│
├── output/
│   └── workpapers/             # Generated workpapers saved here for review
│
└── tests/
    └── test_agent.py
```

---

## The 4 MCP Servers (What Bolt Can Call)

### 1. `ledger_db` — population, testing, sampling
- **`get_population(account, period, control_id)`** — returns the set of items in scope
  for the procedure (transactions / journal entries) with their attributes and any
  supporting-evidence references.
- **`test_items_against_control(control_id, vendor_id=None)`** — runs the control's
  deviation test over the population: missing approval, over delegated authority,
  segregation-of-duties breach, missing supporting doc, out-of-period. Returns a
  deviation list + deviation rate.
- **`sample_population(account, period, method, sample_size)`** — attribute sampling
  (random / monetary-unit). Returns the selected items so testing is reproducible.

### 2. `evidence_registry` — master data + authority
- **`get_master_record(entity_id)`** — vendor/employee master: status, approver,
  related entities, banking, onboarding date.
- **`check_authority_matrix(approver, amount)`** — does this approver hold delegated
  authority for this amount/category? Key control-test signal.

### 3. `criteria_rag` — *** the critical grounding tool ***
- **`query_criteria(query, source="all")`** — semantic search over BOTH corpora.
  `source` ∈ {`"policy"`, `"standard"`, `"all"`}. Returns top chunks with the source
  document, section, and (for standards) the assertion/objective referenced.
- Every workpaper conclusion **must** trace to a criterion returned here. No conclusion
  without a cited criterion. This is what makes Bolt an *audit* tool, not pattern matching.

### 4. `workpaper_rag` — precedent
- **`query_prior_workpapers(query)`** — top 3 prior-year workpapers/findings with their
  conclusion, disposition, and any recurring-deviation note. Used to calibrate severity
  and flag repeat findings.

---

## LangGraph Agent Design

ReAct-style loop, identical topology to Balto:

```
RECEIVE PROCEDURE (objective + control_id + assertion + population scope)
    ↓
PLAN        →  which population? which criteria? what would constitute a deviation?
    ↓
ACT         →  call MCP tools (2–3 rounds): pull population, test, sample,
                retrieve criteria, retrieve prior workpapers
    ↓
SYNTHESIZE  →  cross-reference deviations against criteria + precedent; assess
                deviation rate vs. tolerable; identify what auditor must judge
    ↓
DRAFT WORKPAPER  →  structured output
    ↓
[AUDITOR SIGNS OFF]
```

**AgentState fields:** `procedure` (the objective/control payload), `plan`,
`tool_calls`, `evidence`, `reasoning_trace`, `workpaper`, `act_count`.
Keep Balto's custom `merge_evidence` reducer so evidence accumulates across act rounds.

---

## Workpaper Output Schema

Bolt always produces this structure. **Bolt never issues an opinion — it drafts for sign-off.**

```json
{
  "objective": "string — what this procedure tests",
  "assertion": "string — e.g. Occurrence, Completeness, Authorization, Accuracy",
  "control_id": "string",
  "procedure_performed": "string — what Bolt actually did, in audit language",
  "population_summary": "string — source, period, size, total value",
  "sample": "string — items selected + selection method (or 'full population')",
  "exceptions": ["item ref + nature of deviation + criterion breached"],
  "deviation_rate": "string — e.g. '3 of 40 items (7.5%)' or 'N/A'",
  "criteria_cited": ["policy/standard source + section + clause"],
  "prior_year_reference": ["prior workpaper ref + conclusion + recurrence note"],
  "preliminary_conclusion": "string — e.g. 'Control appears to be operating effectively' / 'Deviations noted; rate exceeds tolerable' — NEVER a final opinion",
  "judgment_note": "string — what the auditor must decide that Bolt cannot",
  "recommended_disposition": "NO EXCEPTION | DEFICIENCY NOTED | ESCALATE — Auditor judgment required",
  "prepared_at": "timestamp"
}
```

> ⚠️ `recommended_disposition` must ALWAYS end with **"— Auditor judgment required"**.
> Enforce this in the memo/workpaper prompt AND validate it in `workpaper_node`.
> `preliminary_conclusion` must never assert a final audit opinion (no "control IS
> effective", no "financials ARE fairly stated") — it describes findings and hands the
> call to the human.

---

## Streamlit UI Conventions

- **Left panel:** Audit-program picker. `procedure_scanner.py` lists pre-built objectives
  (control tests + substantive tests) and pre-flags items that fail a quick rule check.
  Each has a "Run Procedure" button. Plus a custom-procedure form.
- **Center panel:** Live agent reasoning trace, streamed via `st.status()` — `[PLAN]`,
  `[ACT round N]`, `[SYNTHESIZE]`, `[WORKPAPER]`.
- **Right panel:** Workpaper card — disposition badge (green NO EXCEPTION / amber
  DEFICIENCY / red ESCALATE), objective, procedure, exceptions table, cited criteria,
  prior-year reference, judgment note, PDF download.
- Dark theme — it's a projector demo.

---

## Synthetic Data Conventions

- All entities fictional. All amounts USD, $500–$250,000. No real PII.
- **Approval threshold $10,000** (auto-approve below; manual above) — reuse Balto's value.
- Build at least **4 pre-built procedures** with known outcomes so the demo is deterministic:
  1. **Control test — PO approval authority.** Test that every PO ≥ $10k carries a valid
     manual approval by someone with delegated authority. Plant ~2 deviations
     (auto-approved over threshold; approver lacks authority).
  2. **Control test — segregation of duties.** Same person requested + approved a vendor
     or invoice. Plant 1 SoD breach.
  3. **Substantive test — AP occurrence/authorization.** Sample AP items, vouch to
     supporting evidence; plant 1 item with missing/duplicate support.
  4. **Clean procedure.** A control that passes with zero deviations — so Bolt also
     produces "NO EXCEPTION", proving it doesn't flag everything.
- Mark every deviation item so `test_items_against_control` returns deterministic results.

---

## Criteria Corpus (criteria_rag) — IMPORTANT

`criteria_rag` indexes two folders:
- `data/policies/` — internal control policies (fictional, Balto-style: PO approval,
  segregation of duties, vendor onboarding, journal-entry review).
- `data/standards/` — **paraphrased / synthetic** audit-standard summaries. Do NOT copy
  verbatim text from IIA IPPF, PCAOB AS, ISA, COBIT, or SOX. Write short original
  summaries of the *concept* (e.g. "control operating-effectiveness testing",
  "financial-statement assertions: occurrence, completeness, authorization, accuracy,
  cutoff", "sufficient appropriate audit evidence", "tolerable deviation rate") and label
  the file clearly as a synthetic summary for demo purposes. This keeps the artifact
  shareable and copyright-clean.

Each chunk carries metadata: `source`, `section`, and for standards an `assertion` or
`objective` tag so the agent can cite "Occurrence assertion per [synthetic standard], §X".

---

## Demo Narrative (Conference Context)

- Venue: University of Duisburg-Essen, Sept 2–4 2026. Hosted by the Chair of Internal
  Auditing; continuous-auditing track in collaboration with Rutgers CARLAB / WCARS.
- Audience: internal-audit academics + practitioners (Deloitte/PwC/EY/Protiviti/DIIR orbit).
- Frame Bolt as **continuous controls testing with a human-in-the-loop**: the agent runs
  the procedure across the full population in seconds; the auditor exercises judgment on
  the exceptions. Emphasize traceability — every line cites a criterion.
- Key message: **adaptation, not replacement.** Bolt expands what one auditor can test;
  it never removes the auditor's sign-off.

---

## Development Rules

1. **Never hardcode API keys** — `.env` + `python-dotenv`.
2. **Every conclusion traces to a cited criterion** — if `criteria_rag` returns nothing,
   say so; never invent a policy clause or standard reference.
3. **Always stream the trace to the UI** — the live reasoning is the demo.
4. **Keep MCP servers independent** — each runs as its own stdio process.
5. **Workpaper output is always structured JSON** — no free-form verdicts.
6. **`recommended_disposition` always ends with "— Auditor judgment required"** — enforced
   in prompt + validated in node.
7. **No verbatim audit-standard text** — paraphrased/synthetic summaries only.
8. **Deterministic demo** — planted deviations make each procedure reproducible on stage.
9. **Have a canned fallback** — cache one full run in case the API is unavailable on stage.

---

## Environment

```
# .env
ANTHROPIC_API_KEY=your_key_here
```

- Conda env: create a dedicated `bolt` env (`conda create -n bolt python=3.11`).
- In `agent/nodes.py`, set `PYTHON_PATH` to the `bolt` env's python so the MCP servers
  launch in the right interpreter, e.g. `/Users/santo/opt/anaconda3/envs/bolt/bin/python`
  (update to your actual path — `which python` inside the activated env).
- Model: use the current Claude Sonnet API string (`claude-sonnet-4-6`) unless you have a
  reason to pin an older one.

---

## Build Phases (see BUILD_PLAYBOOK.md for the exact Claude Code prompts)

- **Phase 0:** Scaffold + env + requirements.
- **Phase 1:** Synthetic data (population, masters, prior workpapers) + planted deviations.
- **Phase 2:** Criteria corpus (policies + synthetic standards) + ChromaDB ingest.
- **Phase 3:** 4 MCP servers.
- **Phase 4:** LangGraph agent (state, prompts, nodes, graph).
- **Phase 5:** Streamlit UI + procedure scanner + PDF export.
- **Phase 6:** End-to-end wiring, deterministic demo check, canned fallback.
