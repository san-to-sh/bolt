# Bolt — AI Audit Assistant Agent

An AI audit agent that autonomously executes audit procedures and drafts structured workpapers for human sign-off.

**The auditor reaches the opinion. Bolt does the legwork to get them there.**

Built for the 3rd International Conference on Auditing and Artificial Intelligence (University of Duisburg-Essen, Sept 2–4, 2026).

## Quick Start

```bash
conda create -n bolt python=3.11
conda activate bolt
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY
streamlit run app/streamlit_app.py
```

## Architecture

- **Agent**: LangGraph ReAct loop (plan → act → synthesize → workpaper)
- **Tools**: 4 MCP servers (ledger_db, evidence_registry, criteria_rag, workpaper_rag)
- **RAG**: ChromaDB for criteria and prior workpapers
- **UI**: Streamlit 3-column dark-theme interface
