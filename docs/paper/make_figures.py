"""Generate publication-quality figures for the Bolt CFP submission.

Run: python docs/paper/make_figures.py
Outputs PNGs into docs/paper/figures/
"""

import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG_DIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Palette
NAVY = "#1E3A5F"
ORANGE = "#FF6B35"
LBLUE = "#D5E8F0"
LORANGE = "#FFE3D6"
GREY = "#6B7280"
LGREY = "#EEF1F4"
GREEN = "#2E8B57"
AMBER = "#E0A800"
INK = "#1A1A1A"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
})


def panel(ax, x, y, w, h, fc=LBLUE, ec=NAVY, rounded=0.04):
    """Draw a rounded rectangle only."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={rounded}",
        linewidth=1.6, edgecolor=ec, facecolor=fc, zorder=2,
    ))


def box(ax, x, y, w, h, title, sub=None, fc=LBLUE, ec=NAVY, tc=INK,
        fs_title=10, fs_sub=8.5, title_color=None, rounded=0.04):
    """Rounded box with a bold title and optional smaller sub-text.

    Title and sub-text use independent font sizes so a long sub-line never
    inherits the heading size and overflow the box.
    """
    panel(ax, x, y, w, h, fc=fc, ec=ec, rounded=rounded)
    cx = x + w / 2
    if sub:
        ax.text(cx, y + h * 0.66, title, ha="center", va="center",
                fontsize=fs_title, color=title_color or tc, fontweight="bold", zorder=3)
        ax.text(cx, y + h * 0.30, sub, ha="center", va="center",
                fontsize=fs_sub, color=tc, fontweight="normal", zorder=3,
                linespacing=1.35)
    else:
        ax.text(cx, y + h / 2, title, ha="center", va="center",
                fontsize=fs_title, color=title_color or tc, fontweight="bold",
                zorder=3, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, color=NAVY, style="-|>", lw=1.8, rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=15,
        color=color, lw=lw, linestyle=ls,
        connectionstyle=f"arc3,rad={rad}", zorder=1,
    ))


# ---------------------------------------------------------------------------
# Figure 1 — Agent topology (LangGraph ReAct loop)
# ---------------------------------------------------------------------------
def fig_topology():
    fig, ax = plt.subplots(figsize=(7.6, 8.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    cx, bw, bh = 1.7, 5.8, 1.18
    mid = cx + bw / 2  # 4.6

    box(ax, cx, 10.4, bw, bh, "RECEIVE PROCEDURE",
        "objective  ·  assertion  ·  control_id  ·  scope",
        fc=LGREY, ec=GREY, fs_title=10.5, fs_sub=9)
    box(ax, cx, 8.7, bw, bh, "PLAN",
        "Which population?  Which criteria?\nWhat constitutes a deviation?",
        fc=LBLUE, fs_title=10.5, fs_sub=9)
    box(ax, cx, 7.0, bw, bh, "ACT   (ReAct tool calls)",
        "pull  ·  test  ·  sample  ·  cite  ·  precedent",
        fc=LORANGE, ec=ORANGE, fs_title=10.5, fs_sub=9)
    box(ax, cx, 5.3, bw, bh, "SYNTHESIZE",
        "deviations  ×  criteria  ×  precedent",
        fc=LBLUE, fs_title=10.5, fs_sub=9)
    box(ax, cx, 3.6, bw, bh, "DRAFT WORKPAPER",
        "structured JSON  →  validate disposition",
        fc=LBLUE, fs_title=10.5, fs_sub=9)
    box(ax, cx, 1.9, bw, bh, "[ AUDITOR SIGNS OFF ]",
        "professional judgment on exceptions",
        fc="#E9F7EF", ec=GREEN, fs_title=10.5, fs_sub=9)

    for y in [10.4, 8.7, 7.0, 5.3, 3.6]:
        arrow(ax, mid, y, mid, y - 0.52)

    # sufficiency self-loop on ACT
    box(ax, 8.05, 6.95, 1.55, 1.28, "Sufficiency",
        "check\n(≤ 3 rounds)", fc="#FFF7E6", ec=AMBER, fs_title=9, fs_sub=8.5)
    arrow(ax, cx + bw, 7.85, 8.05, 7.75, color=AMBER, rad=-0.25)
    arrow(ax, 8.05, 7.25, cx + bw, 7.05, color=AMBER, rad=-0.25)
    ax.text(8.82, 8.45, "insufficient", ha="center", fontsize=8, color=AMBER, style="italic")

    ax.text(mid, 0.95, "Invariant: every conclusion traces to a cited criterion",
            ha="center", fontsize=9.5, color=ORANGE, style="italic", fontweight="bold")
    ax.text(mid, 11.7, "Figure 1.  Bolt agent topology (LangGraph StateGraph)",
            ha="center", fontsize=11.5, color=NAVY, fontweight="bold")

    fig.savefig(os.path.join(FIG_DIR, "fig1_topology.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 — System architecture (agent + 4 MCP servers + data)
# ---------------------------------------------------------------------------
def fig_architecture():
    fig, ax = plt.subplots(figsize=(13.0, 7.6))
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 9.4)
    ax.axis("off")

    cxc = 6.75  # canvas centre

    # UI layer
    box(ax, 1.0, 8.05, 11.5, 0.9, "Streamlit UI   (3-column dark theme)",
        "procedure picker   |   live reasoning trace   |   workpaper card",
        fc=LGREY, ec=GREY, fs_title=10, fs_sub=9)
    arrow(ax, cxc, 8.05, cxc, 7.6, color=GREY)

    # Agent layer
    box(ax, 3.25, 6.35, 7.0, 1.15, "LangGraph Agent   ·   Claude Sonnet",
        "plan → act → synthesize → workpaper",
        fc=NAVY, ec=NAVY, tc="white", title_color="white", fs_title=11, fs_sub=9.5)

    # MCP servers
    sw = 2.85
    sx = [0.45, 3.73, 7.01, 10.29]
    centres = [x + sw / 2 for x in sx]
    servers = [
        ("ledger_db", "get_population\ntest_items_against_control\nsample_population", LBLUE, NAVY),
        ("evidence_registry", "get_master_record\ncheck_authority_matrix", LBLUE, NAVY),
        ("criteria_rag  ★", "query_criteria\n(policy | standard | all)", LORANGE, ORANGE),
        ("workpaper_rag", "query_prior_workpapers", LBLUE, NAVY),
    ]
    for x, c, (name, tools, fc, ec) in zip(sx, centres, servers):
        box(ax, x, 3.65, sw, 1.85, name, tools, fc=fc, ec=ec,
            fs_title=9.5, fs_sub=7.8)
        arrow(ax, cxc, 6.35, c, 5.55, color=ec, lw=1.5)
        lx = (cxc + c) / 2 + (0.18 if c > cxc else -0.18)
        ax.text(lx, 6.0, "stdio", fontsize=7.5, color=ec, style="italic", ha="center")

    # Data sources
    data = [
        ("transactions.json", "25 items", LGREY, GREY),
        ("masters.json", "10 vendors  ·  4 approvers", LGREY, GREY),
        ("ChromaDB ‘criteria’", "43 chunks", "#FFF1E8", ORANGE),
        ("ChromaDB ‘prior_workpapers’", "8 docs", LGREY, GREY),
    ]
    for x, c, (t, s, fc, ec) in zip(sx, centres, data):
        box(ax, x, 1.85, sw, 1.05, t, s, fc=fc, ec=ec, fs_title=8.6, fs_sub=8.3)
        arrow(ax, c, 3.65, c, 2.95, color=GREY, lw=1.4)

    ax.text(cxc, 0.95,
            "★ criteria_rag is the grounding layer: no workpaper conclusion without a cited criterion",
            ha="center", fontsize=9.5, color=ORANGE, style="italic", fontweight="bold")
    ax.text(cxc, 9.1, "Figure 2.  System architecture — agent, four MCP tool servers, and data sources",
            ha="center", fontsize=11.5, color=NAVY, fontweight="bold")

    fig.savefig(os.path.join(FIG_DIR, "fig2_architecture.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 — Data / RAG ingestion pipeline
# ---------------------------------------------------------------------------
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 7)
    ax.axis("off")

    box(ax, 0.4, 5.25, 3.0, 1.0, "data/policies/*.md", "4 control policies", fc=LBLUE, fs_title=9, fs_sub=8.5)
    box(ax, 0.4, 3.95, 3.0, 1.0, "data/standards/*.md", "3 synthetic summaries", fc=LBLUE, fs_title=9, fs_sub=8.5)
    box(ax, 0.4, 2.35, 3.0, 1.0, "prior_workpapers.json", "8 prior-year WPs", fc=LBLUE, fs_title=9, fs_sub=8.5)
    box(ax, 0.4, 0.75, 3.0, 1.0, "transactions.json", "masters.json", fc=LGREY, ec=GREY, fs_title=9, fs_sub=8.5)

    box(ax, 4.5, 3.75, 2.6, 1.45, "ingest.py", "chunk by ‘##’\n+ metadata tags",
        fc=LORANGE, ec=ORANGE, fs_title=9.5, fs_sub=8.5)
    arrow(ax, 3.4, 5.75, 4.5, 4.9)
    arrow(ax, 3.4, 4.45, 4.5, 4.55)
    arrow(ax, 3.4, 2.85, 4.5, 4.2)

    box(ax, 8.2, 4.65, 3.6, 1.15, "ChromaDB ‘criteria’", "43 chunks  (28 policy / 15 std)",
        fc="#FFF1E8", ec=ORANGE, fs_title=9, fs_sub=8.3)
    box(ax, 8.2, 3.1, 3.6, 1.15, "ChromaDB ‘prior_workpapers’", "8 documents",
        fc="#FFF1E8", ec=ORANGE, fs_title=9, fs_sub=8.3)
    arrow(ax, 7.1, 4.65, 8.2, 5.2, color=ORANGE)
    arrow(ax, 7.1, 4.3, 8.2, 3.65, color=ORANGE)

    box(ax, 8.2, 0.75, 3.6, 1.05, "ledger_db / evidence_registry", "(direct JSON read)",
        fc=LGREY, ec=GREY, fs_title=8.6, fs_sub=8.3)
    arrow(ax, 1.9, 0.75, 1.9, 0.45, color=GREY, style="-")
    arrow(ax, 1.9, 0.45, 9.9, 0.45, color=GREY, style="-|>")

    ax.text(9.45, 2.5, "all-MiniLM-L6-v2 local embeddings", ha="center", fontsize=8, color=GREY, style="italic")
    ax.text(6.25, 6.65, "Figure 3.  Data ingestion and retrieval-augmented grounding pipeline",
            ha="center", fontsize=11.5, color=NAVY, fontweight="bold")

    fig.savefig(os.path.join(FIG_DIR, "fig3_pipeline.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 — Human-in-the-loop division of labour
# ---------------------------------------------------------------------------
def fig_hitl():
    fig, ax = plt.subplots(figsize=(10.4, 5.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    panel(ax, 0.5, 1.3, 5.0, 3.4, fc="#FBFCFE", ec=ORANGE, rounded=0.02)
    ax.text(3.0, 4.35, "BOLT  —  the legwork (automated)", ha="center", fontsize=10.5,
            color=ORANGE, fontweight="bold")
    bolt_items = [
        "Pull the full population in scope",
        "Test every item against the control",
        "Retrieve governing policy + standard",
        "Find prior-year precedent",
        "Compute the deviation rate",
        "Draft the structured workpaper",
    ]
    for i, it in enumerate(bolt_items):
        ax.text(0.85, 3.85 - i * 0.42, "•  " + it, fontsize=9, color=INK, va="center")

    panel(ax, 6.5, 1.3, 5.0, 3.4, fc="#FBFFFB", ec=GREEN, rounded=0.02)
    ax.text(9.0, 4.35, "AUDITOR  —  the opinion (judgment)", ha="center", fontsize=10.5,
            color=GREEN, fontweight="bold")
    aud_items = [
        "Weigh severity of each exception",
        "Decide tolerable vs. excessive deviation",
        "Assess fraud risk and intent",
        "Determine scope expansion",
        "Reach the audit conclusion",
        "Sign the workpaper",
    ]
    for i, it in enumerate(aud_items):
        ax.text(6.85, 3.85 - i * 0.42, "•  " + it, fontsize=9, color=INK, va="center")

    arrow(ax, 5.5, 3.0, 6.5, 3.0, color=NAVY, lw=2.4)
    ax.text(6.0, 3.35, "hand-off", ha="center", fontsize=8.5, color=NAVY, style="italic")

    ax.text(6.0, 0.75,
            "Adaptation, not replacement — Bolt expands what one auditor can test; it never removes the sign-off.",
            ha="center", fontsize=9, color=NAVY, style="italic")
    ax.text(6.0, 5.55, "Figure 4.  Human-in-the-loop division of labour",
            ha="center", fontsize=11.5, color=NAVY, fontweight="bold")

    fig.savefig(os.path.join(FIG_DIR, "fig4_hitl.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_topology()
    fig_architecture()
    fig_pipeline()
    fig_hitl()
    print("Figures written to", FIG_DIR)
    for f in sorted(os.listdir(FIG_DIR)):
        print(" -", f, f"({os.path.getsize(os.path.join(FIG_DIR, f)):,} bytes)")
