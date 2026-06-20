"""Generate a formatted architecture PDF from architecture.md content.

Usage: python docs/generate_architecture_pdf.py
Output: docs/bolt_architecture.pdf
"""

import os
from fpdf import FPDF


def _safe(text: str) -> str:
    return text.encode("latin-1", errors="replace").decode("latin-1")


class ArchitecturePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, _safe("Bolt — AI Audit Assistant | System Architecture"), align="R")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 60, 120)
        self.cell(0, 10, _safe(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 120)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def subsection_title(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, _safe(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, _safe(text))
        self.ln(3)

    def mono_block(self, text: str):
        self.set_font("Courier", "", 8)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        y = self.get_y()
        lines = text.split("\n")
        block_height = len(lines) * 4.5 + 4
        if y + block_height > self.h - self.b_margin:
            self.add_page()
        self.rect(self.l_margin, self.get_y(), self.w - self.l_margin - self.r_margin, block_height, "F")
        self.ln(2)
        for line in lines:
            self.cell(0, 4.5, _safe(f"  {line}"), new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def table_row(self, cells: list[str], widths: list[float], bold: bool = False):
        self.set_font("Helvetica", "B" if bold else "", 8)
        self.set_text_color(30, 30, 30)
        h = 6
        for i, (cell, w) in enumerate(zip(cells, widths)):
            self.cell(w, h, _safe(cell), border=1)
        self.ln(h)


def generate():
    pdf = ArchitecturePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title page
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(30, 60, 120)
    pdf.ln(30)
    pdf.cell(0, 15, _safe("Bolt"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, _safe("AI Audit Assistant — System Architecture"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, _safe("The auditor reaches the opinion. Bolt does the legwork."), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, _safe("3rd International Conference on Auditing and Artificial Intelligence"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe("University of Duisburg-Essen | September 2-4, 2026"), align="C", new_x="LMARGIN", new_y="NEXT")

    # Section 1: Design Philosophy
    pdf.add_page()
    pdf.section_title("1. Design Philosophy")
    pdf.body_text(
        "Bolt is an AI audit agent that autonomously executes audit procedures and drafts "
        "structured workpapers for human sign-off. It demonstrates continuous controls testing "
        "with a human-in-the-loop: the agent runs each procedure across the full population "
        "in seconds; the auditor exercises professional judgment on the exceptions."
    )
    pdf.body_text(
        "The system enforces a strict separation between evidence-gathering (automated) and "
        "opinion-forming (human). Bolt never issues a final audit opinion. Every conclusion "
        "must trace to a criterion returned by the criteria RAG layer."
    )

    # Section 2: Agent Topology
    pdf.section_title("2. Agent Topology (LangGraph)")
    pdf.body_text(
        "Bolt uses a ReAct-style loop implemented as a LangGraph StateGraph with four node "
        "types and a conditional edge for act-round sufficiency checking (hard cap: 3 rounds)."
    )
    pdf.mono_block(
        "RECEIVE PROCEDURE\n"
        "    |\n"
        "    v\n"
        "  PLAN  -->  which population? which criteria?\n"
        "    |\n"
        "    v\n"
        "  ACT  <-->  sufficiency check (max 3 rounds)\n"
        "    |\n"
        "    v\n"
        "  SYNTHESIZE  -->  deviations x criteria x precedent\n"
        "    |\n"
        "    v\n"
        "  WORKPAPER  -->  structured JSON, validated\n"
        "    |\n"
        "    v\n"
        "  [AUDITOR SIGNS OFF]"
    )

    pdf.subsection_title("AgentState Fields")
    cols = [35, 25, 25, 85]
    pdf.table_row(["Field", "Type", "Reducer", "Purpose"], cols, bold=True)
    rows = [
        ["procedure", "dict", "--", "Objective, assertion, control_id, account"],
        ["plan", "str", "--", "Natural-language audit plan"],
        ["tool_calls", "list[dict]", "operator.add", "Accumulated tool invocations"],
        ["evidence", "dict", "merge_evidence", "Deduplicated evidence from tools"],
        ["reasoning_trace", "list[str]", "operator.add", "Streaming trace for UI"],
        ["workpaper", "dict", "--", "Final structured output"],
        ["act_count", "int", "--", "Loop counter (max 3)"],
    ]
    for row in rows:
        pdf.table_row(row, cols)
    pdf.ln(4)

    # Section 3: Tool Layer
    pdf.section_title("3. Tool Layer (4 MCP Servers)")
    pdf.body_text(
        "Bolt communicates with four MCP servers over stdio. Each server is an independent "
        "process launched by the MCPManager async context manager using AsyncExitStack."
    )

    cols3 = [30, 40, 100]
    pdf.table_row(["Server", "Tools", "Data Source"], cols3, bold=True)
    tools = [
        ["ledger_db", "get_population, test_items,\nsample_population", "transactions.json"],
        ["evidence_registry", "get_master_record,\ncheck_authority_matrix", "masters.json"],
        ["criteria_rag", "query_criteria", "ChromaDB 'criteria' (43 chunks)"],
        ["workpaper_rag", "query_prior_workpapers", "ChromaDB 'prior_workpapers' (8 docs)"],
    ]
    for row in tools:
        pdf.table_row(row, cols3)
    pdf.ln(4)

    pdf.subsection_title("criteria_rag: The Critical Grounding Tool")
    pdf.body_text(
        "Every workpaper conclusion must cite a criterion returned by criteria_rag. It indexes "
        "two corpora: 4 internal control policies (28 chunks) and 3 synthetic audit standard "
        "summaries (15 chunks). Standards are tagged with assertion and objective metadata for "
        "filtered retrieval. All standard text is original — no verbatim published standards."
    )

    # Section 4: Workpaper Schema
    pdf.add_page()
    pdf.section_title("4. Workpaper Output Schema")
    pdf.body_text(
        "Bolt always produces a structured JSON workpaper. The recommended_disposition field "
        "must end with '-- Auditor judgment required' — enforced in the prompt and validated "
        "in workpaper_node. The preliminary_conclusion must never assert a final opinion."
    )

    cols4 = [45, 22, 103]
    pdf.table_row(["Field", "Type", "Constraint"], cols4, bold=True)
    schema = [
        ["objective", "string", "What this procedure tests"],
        ["assertion", "string", "e.g. Authorization, Occurrence"],
        ["control_id", "string", "CTRL-01 through CTRL-04"],
        ["procedure_performed", "string", "What Bolt did, in audit language"],
        ["population_summary", "string", "Source, period, size, total value"],
        ["sample", "string", "Items selected + method"],
        ["exceptions", "list", "Item ref + deviation + criterion breached"],
        ["deviation_rate", "string", "e.g. '2 of 9 items (22.2%)'"],
        ["criteria_cited", "list", "Policy/standard + section + clause"],
        ["prior_year_reference", "list", "Prior WP ref + conclusion + recurrence"],
        ["preliminary_conclusion", "string", "NEVER a final opinion"],
        ["judgment_note", "string", "What auditor must decide"],
        ["recommended_disposition", "string", "Ends with 'Auditor judgment required'"],
        ["prepared_at", "string", "ISO timestamp"],
    ]
    for row in schema:
        pdf.table_row(row, cols4)
    pdf.ln(4)

    # Section 5: Demo Procedures
    pdf.section_title("5. Demo Procedures")
    pdf.body_text(
        "Four pre-built procedures with deterministic planted deviations ensure reproducible "
        "demo results. The pre-scan badges in the UI show expected flag counts before running."
    )

    cols5 = [20, 55, 65, 30]
    pdf.table_row(["Control", "Test", "Planted Deviations", "Disposition"], cols5, bold=True)
    procs = [
        ["CTRL-01", "PO approval authority", "TXN-003 authority exceeded,\nTXN-004 auto-approved", "DEFICIENCY"],
        ["CTRL-02", "Segregation of duties", "TXN-011 requestor==approver", "DEFICIENCY"],
        ["CTRL-03", "Substantive AP test", "TXN-016 missing doc,\nTXN-019 duplicate", "ESCALATE"],
        ["CTRL-04", "Journal entry review", "(none -- clean control)", "NO EXCEPTION"],
    ]
    for row in procs:
        pdf.table_row(row, cols5)
    pdf.ln(4)

    # Section 6: Reliability
    pdf.section_title("6. Reliability and Demo Mode")
    pdf.body_text(
        "Tenacity retry on Anthropic 529 (overloaded) errors with exponential backoff. "
        "JSON parse fallback in workpaper_node preserves raw LLM output on parse failure. "
        "Demo mode (sidebar toggle or BOLT_DEMO_MODE env var) loads pre-cached workpapers "
        "for API-free presentations. The cache is refreshed via capture_demo_cache.py."
    )

    # Section 7: Tech Stack
    pdf.section_title("7. Technology Stack")
    cols7 = [40, 130]
    pdf.table_row(["Layer", "Technology"], cols7, bold=True)
    stack = [
        ["LLM", "Claude Sonnet (Anthropic) via langchain-anthropic"],
        ["Agent Framework", "LangGraph (StateGraph, ReAct loop)"],
        ["Tool Integration", "MCP (Model Context Protocol) over stdio"],
        ["RAG", "ChromaDB (persistent, local embeddings)"],
        ["UI", "Streamlit (3-column, dark theme)"],
        ["Data", "Synthetic JSON + Markdown criteria docs"],
        ["Language", "Python 3.11"],
    ]
    for row in stack:
        pdf.table_row(row, cols7)

    out_path = os.path.join(os.path.dirname(__file__), "bolt_architecture.pdf")
    pdf.output(out_path)
    print(f"Generated: {out_path} ({os.path.getsize(out_path):,} bytes)")


if __name__ == "__main__":
    generate()
