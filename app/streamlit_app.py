"""Main Streamlit UI — procedure picker, live trace, and workpaper display."""

import asyncio
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone

import streamlit as st
from fpdf import FPDF
from streamlit.runtime.scriptrunner import add_script_run_ctx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.procedure_scanner import get_procedures

st.set_page_config(page_title="Bolt — AI Audit Assistant", layout="wide", page_icon="⚡")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "workpapers")
DEMO_CACHE_DIR = os.path.join(OUTPUT_DIR, "demo_cache")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEMO_MODE_ENV = os.environ.get("BOLT_DEMO_MODE", "").lower() in ("1", "true", "yes")

# ── Session state defaults ──────────────────────────────────────────────────
for key, default in {
    "workpaper": None,
    "trace": [],
    "running": False,
    "run_complete": False,
    "demo_mode": DEMO_MODE_ENV,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Demo mode: load cached workpapers ────────────────────────────────────────
def _load_demo_cache(control_id: str) -> dict | None:
    path = os.path.join(DEMO_CACHE_DIR, f"{control_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _start_demo_run(proc: dict):
    control_id = proc.get("control_id", "")
    cached = _load_demo_cache(control_id)
    if cached:
        st.session_state.workpaper = cached
        st.session_state.trace = [
            "[DEMO MODE] Loaded cached workpaper from demo_cache/",
            f"[WORKPAPER] Drafted — disposition: {cached.get('recommended_disposition', 'UNKNOWN')}",
        ]
        st.session_state.run_complete = True
        st.session_state.running = False
    else:
        st.session_state.trace = [f"[ERROR] No demo cache found for {control_id}"]
        st.session_state.run_complete = True
        st.session_state.running = False


# ── Async / sync bridge ─────────────────────────────────────────────────────
def _run_in_thread(proc: dict):
    """Run the agent in a background thread with its own event loop."""
    loop = asyncio.new_event_loop()

    async def _execute():
        from agent.graph import run_procedure

        state = await run_procedure(proc)
        st.session_state.workpaper = state.get("workpaper", {})
        st.session_state.trace = state.get("reasoning_trace", [])
        st.session_state.run_complete = True

    try:
        loop.run_until_complete(_execute())
    except Exception as e:
        st.session_state.trace.append(f"[ERROR] {e}")
        st.session_state.run_complete = True
    finally:
        loop.close()


def _start_run(proc: dict):
    st.session_state.running = True
    st.session_state.run_complete = False
    st.session_state.workpaper = None
    st.session_state.trace = ["[STARTING] Launching audit procedure..."]
    thread = threading.Thread(target=_run_in_thread, args=(proc,), daemon=True)
    add_script_run_ctx(thread)
    thread.start()


# ── Markdown-safe rendering ─────────────────────────────────────────────────
def _md(text) -> str:
    """Escape characters st.markdown would otherwise misinterpret (e.g. '$' as LaTeX math)."""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("$", "\\$")


# ── PDF builder ──────────────────────────────────────────────────────────────
def _pdf_safe(text: str) -> str:
    """Sanitize text for fpdf2 (latin-1 safe)."""
    if not isinstance(text, str):
        text = str(text)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _build_pdf(wp: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_safe("Bolt Audit Workpaper"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _pdf_safe(f"Prepared: {wp.get('prepared_at', '')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _pdf_safe(f"Disposition: {wp.get('recommended_disposition', '')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    sections = [
        ("Objective", wp.get("objective", "")),
        ("Assertion", wp.get("assertion", "")),
        ("Control ID", wp.get("control_id", "")),
        ("Procedure Performed", wp.get("procedure_performed", "")),
        ("Population Summary", wp.get("population_summary", "")),
        ("Sample", wp.get("sample", "")),
        ("Deviation Rate", wp.get("deviation_rate", "")),
        ("Preliminary Conclusion", wp.get("preliminary_conclusion", "")),
        ("Judgment Note", wp.get("judgment_note", "")),
    ]

    for title, content in sections:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _pdf_safe(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _pdf_safe(content))
        pdf.ln(3)

    list_sections = [
        ("Exceptions", wp.get("exceptions", [])),
        ("Criteria Cited", wp.get("criteria_cited", [])),
        ("Prior Year Reference", wp.get("prior_year_reference", [])),
    ]

    for title, items in list_sections:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _pdf_safe(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        if items:
            for item in items:
                pdf.multi_cell(0, 5, _pdf_safe(f"  - {item}"))
                pdf.ln(1)
        else:
            pdf.cell(0, 5, _pdf_safe("  (none)"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, _pdf_safe("Generated by Bolt AI Audit Assistant. Auditor sign-off required."), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Bolt")
    st.caption("AI Audit Assistant")
    st.divider()
    st.session_state.demo_mode = st.toggle(
        "Demo Mode (cached results)",
        value=st.session_state.demo_mode,
        help="When on, loads pre-cached workpapers instead of calling the API. Use for demos or when API is unavailable.",
    )
    if st.session_state.demo_mode:
        st.info("Demo mode: using cached workpapers")
    st.divider()
    st.caption("3rd Intl. Conference on Auditing & AI\nUniversity of Duisburg-Essen, Sept 2–4, 2026")

# ── Layout ───────────────────────────────────────────────────────────────────
left, center, right = st.columns([1, 2, 2])

# ── LEFT: Procedure picker ──────────────────────────────────────────────────
with left:
    st.header("Audit Program")
    procedures = get_procedures()

    for proc in procedures:
        badge = ""
        if proc["flag_count"] > 0:
            badge = f' :red[{proc["flag_count"]} flag{"s" if proc["flag_count"] != 1 else ""}]'
        elif proc["flag_count"] == 0:
            badge = " :green[clean]"

        with st.expander(f'{proc["id"]} — {proc["description"][:45]}...{badge}'):
            st.markdown(f'**Objective:** {_md(proc["objective"])}')
            st.markdown(f'**Assertion:** {_md(proc["assertion"])}')
            st.markdown(f'**Control:** {_md(proc["control_id"])}')

            if proc["pre_scan_flags"]:
                st.markdown("**Pre-scan flags:**")
                for flag in proc["pre_scan_flags"]:
                    st.markdown(f"- `{flag}`")

            run_proc = {
                "objective": proc["objective"],
                "assertion": proc["assertion"],
                "control_id": proc["control_id"],
                "account": proc["account"],
                "period": proc["period"],
            }

            if st.button(
                "Run Procedure",
                key=f'run_{proc["id"]}',
                disabled=st.session_state.running,
                use_container_width=True,
            ):
                if st.session_state.demo_mode:
                    _start_demo_run(run_proc)
                else:
                    _start_run(run_proc)
                st.rerun()

    st.divider()
    st.subheader("Custom Procedure")
    with st.form("custom_proc"):
        c_obj = st.text_input("Objective")
        c_assertion = st.text_input("Assertion", value="Authorization")
        c_control = st.text_input("Control ID")
        c_account = st.text_input("Account", value="AP")
        c_period = st.text_input("Period", value="2025-2026")
        submitted = st.form_submit_button("Run Custom", disabled=st.session_state.running)
        if submitted and c_obj and c_control:
            custom = {
                "objective": c_obj,
                "assertion": c_assertion,
                "control_id": c_control,
                "account": c_account,
                "period": c_period,
            }
            if st.session_state.demo_mode:
                _start_demo_run(custom)
            else:
                _start_run(custom)
            st.rerun()


# ── CENTER: Live reasoning trace ─────────────────────────────────────────────
with center:
    st.header("Reasoning Trace")

    if st.session_state.running and not st.session_state.run_complete:
        st.info("Agent is running... this page will update when complete.")
        import time

        time.sleep(2)
        st.rerun()

    if st.session_state.run_complete:
        st.session_state.running = False

    trace = st.session_state.trace
    if trace:
        for entry in trace:
            if entry.startswith("[PLAN]"):
                with st.status("PLAN", state="complete"):
                    st.markdown(_md(entry[6:].strip()))
            elif entry.startswith("[ACT round"):
                label = entry.split("]")[0] + "]"
                with st.status(label, state="complete"):
                    st.text(entry[len(label):].strip())
            elif entry.startswith("[SYNTHESIZE]"):
                with st.status("SYNTHESIZE", state="complete"):
                    st.markdown(_md(entry[12:].strip()))
            elif entry.startswith("[WORKPAPER]"):
                with st.status("WORKPAPER", state="complete"):
                    st.text(entry[11:].strip())
            elif entry.startswith("[ERROR]"):
                st.error(entry)
            elif entry.startswith("[STARTING]"):
                st.info(entry[10:].strip())
            else:
                st.text(entry)
    else:
        st.caption("Select a procedure and click 'Run Procedure' to begin.")


# ── RIGHT: Workpaper card ────────────────────────────────────────────────────
with right:
    st.header("Workpaper")
    wp = st.session_state.workpaper

    if wp:
        disposition = wp.get("recommended_disposition", "")
        if "ESCALATE" in disposition.upper():
            st.error(f"DISPOSITION: {_md(disposition)}")
        elif "DEFICIENCY" in disposition.upper():
            st.warning(f"DISPOSITION: {_md(disposition)}")
        elif "NO EXCEPTION" in disposition.upper():
            st.success(f"DISPOSITION: {_md(disposition)}")
        else:
            st.info(f"DISPOSITION: {_md(disposition)}")

        st.markdown(f'**Objective:** {_md(wp.get("objective", ""))}')
        st.markdown(f'**Assertion:** {_md(wp.get("assertion", ""))}')
        st.markdown(f'**Control ID:** {_md(wp.get("control_id", ""))}')
        st.divider()

        st.markdown(f'**Procedure Performed:**\n{_md(wp.get("procedure_performed", ""))}')
        st.markdown(f'**Population:** {_md(wp.get("population_summary", ""))}')
        st.markdown(f'**Sample:** {_md(wp.get("sample", ""))}')
        st.markdown(f'**Deviation Rate:** {_md(wp.get("deviation_rate", ""))}')
        st.divider()

        exceptions = wp.get("exceptions", [])
        if exceptions:
            st.markdown("**Exceptions:**")
            for exc in exceptions:
                st.markdown(f"- {_md(exc)}")
        else:
            st.markdown("**Exceptions:** None")

        st.divider()
        criteria = wp.get("criteria_cited", [])
        if criteria:
            st.markdown("**Criteria Cited:**")
            for c in criteria:
                st.markdown(f"- {_md(c)}")

        prior = wp.get("prior_year_reference", [])
        if prior:
            st.markdown("**Prior Year Reference:**")
            for p in prior:
                st.markdown(f"- {_md(p)}")

        st.divider()
        st.markdown(f'**Preliminary Conclusion:**\n{_md(wp.get("preliminary_conclusion", ""))}')
        st.markdown(f'**Judgment Note:**\n{_md(wp.get("judgment_note", ""))}')

        st.divider()
        pdf_bytes = _build_pdf(wp)
        control_id = wp.get("control_id", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workpaper_{control_id}_{ts}.pdf"

        st.download_button(
            label="Download Workpaper PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )

        wp_path = os.path.join(OUTPUT_DIR, f"workpaper_{control_id}_{ts}.json")
        with open(wp_path, "w") as f:
            json.dump(wp, f, indent=2)
    else:
        st.caption("No workpaper yet. Run a procedure to generate one.")
