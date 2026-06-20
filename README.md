# Bolt — AI Audit Assistant Agent

**The auditor reaches the opinion. Bolt does the legwork to get them there.**

Bolt is an AI audit agent built for the **3rd International Conference on Auditing and Artificial Intelligence** (University of Duisburg-Essen, Sept 2–4, 2026). An auditor selects an audit procedure — a control test or substantive test tied to an objective and assertion — and Bolt autonomously pulls the relevant population, tests items against control criteria, retrieves governing policies and audit standards, finds prior-year workpapers for precedent, and drafts a structured audit workpaper for the auditor to review and sign off. Bolt demonstrates continuous controls testing with a human-in-the-loop: the agent runs each procedure across the full population in seconds while the auditor exercises judgment on the exceptions. Every conclusion traces to a cited criterion. The key message is **adaptation, not replacement** — Bolt expands what one auditor can test; it never removes the auditor's sign-off.

## Setup

```bash
# 1. Create and activate conda environment
conda create -n bolt python=3.11 -y
conda activate bolt

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Ingest criteria corpus into ChromaDB
python data/ingest.py

# 5. Run the app
streamlit run app/streamlit_app.py
```

## Demo Mode

For presentations or when the API is unavailable, enable demo mode to use cached workpapers:

```bash
# Via environment variable
BOLT_DEMO_MODE=true streamlit run app/streamlit_app.py

# Or toggle the "Demo Mode" switch in the sidebar
```

To refresh the demo cache with live API results:

```bash
python scripts/capture_demo_cache.py
```

## Demo Procedures

Bolt ships with four pre-built audit procedures, each with deterministic planted deviations:

| Procedure | Control | What It Tests | Expected Disposition |
|-----------|---------|---------------|---------------------|
| **PROC-1** | CTRL-01 | PO approval authority — every PO >= $10,000 must carry valid manual approval by an authorized approver | **DEFICIENCY NOTED** (2 deviations: TXN-003 authority exceeded, TXN-004 auto-approved above threshold) |
| **PROC-2** | CTRL-02 | Segregation of duties — no single individual both requests and approves a purchase | **DEFICIENCY NOTED** (1 deviation: TXN-011 requestor == approver) |
| **PROC-3** | CTRL-03 | Substantive AP test — vouch payments to supporting docs, scan for duplicates | **ESCALATE** (2 deviations: TXN-016 missing doc, TXN-019 duplicate invoice) |
| **PROC-4** | CTRL-04 | Journal entry review controls — expected clean | **NO EXCEPTION** (0 deviations) |

## Architecture

```
RECEIVE PROCEDURE (objective + control_id + assertion)
    ↓
PLAN        →  which population? which criteria? what constitutes a deviation?
    ↓
ACT         →  call MCP tools (2–3 rounds): pull population, test, retrieve criteria
    ↓
SYNTHESIZE  →  cross-reference deviations against criteria + precedent
    ↓
DRAFT WORKPAPER  →  structured JSON output
    ↓
[AUDITOR SIGNS OFF]
```

| Layer | Technology |
|---|---|
| LLM | Claude Sonnet (Anthropic) via `langchain-anthropic` |
| Agent Framework | LangGraph (StateGraph, ReAct loop) |
| Tool Integration | MCP (Model Context Protocol) over stdio |
| RAG | ChromaDB (persistent, local embeddings) |
| UI | Streamlit (3-column, dark theme) |
| Data | Synthetic JSON + Markdown criteria docs |

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
bolt/
├── agent/           # LangGraph agent (state, prompts, nodes, graph)
├── app/             # Streamlit UI + procedure scanner
├── mcp_servers/     # 4 MCP tool servers (ledger_db, evidence_registry, criteria_rag, workpaper_rag)
├── data/
│   ├── synthetic/   # Transactions, masters, prior workpapers
│   ├── policies/    # Internal control policies (Markdown)
│   ├── standards/   # Synthetic audit standard summaries (Markdown)
│   └── ingest.py    # ChromaDB ingestion script
├── output/workpapers/demo_cache/  # Cached workpapers for demo mode
├── scripts/         # Utility scripts (capture_demo_cache.py)
└── tests/           # pytest test suite
```
