"""Ingest policies, standards, and prior workpapers into ChromaDB.

- 'criteria' collection: policies chunked by '## ' section, standards chunked by
  section with assertion/objective metadata.
- 'prior_workpapers' collection: one document per prior-year workpaper.

Persists to ./chroma_data relative to this script's directory.
"""

import json
import os
import re
import chromadb

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(DATA_DIR, "..", "chroma_data")
POLICIES_DIR = os.path.join(DATA_DIR, "policies")
STANDARDS_DIR = os.path.join(DATA_DIR, "standards")

ASSERTION_KEYWORDS = {
    "occurrence": "occurrence",
    "completeness": "completeness",
    "authorization": "authorization",
    "accuracy": "accuracy",
    "cutoff": "cutoff",
    "existence": "existence",
    "rights and obligations": "rights_and_obligations",
    "valuation": "valuation_and_allocation",
}

OBJECTIVE_KEYWORDS = {
    "design effectiveness": "design_vs_operating_effectiveness",
    "operating effectiveness": "design_vs_operating_effectiveness",
    "deviation rate": "deviation_rate_assessment",
    "tolerable rate": "deviation_rate_assessment",
    "sample size": "sampling_methodology",
    "sampling": "sampling_methodology",
    "sufficient": "sufficient_appropriate_evidence",
    "appropriate": "sufficient_appropriate_evidence",
    "audit evidence": "sufficient_appropriate_evidence",
}


def chunk_by_section(text: str) -> list[dict]:
    """Split markdown into chunks at '## ' headers. Returns list of {section, body}."""
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        section = lines[0].lstrip("#").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if body:
            chunks.append({"section": section, "body": body})
    return chunks


def detect_assertion(text: str) -> str | None:
    lower = text.lower()
    for keyword, assertion in ASSERTION_KEYWORDS.items():
        if keyword in lower:
            return assertion
    return None


def detect_objective(text: str) -> str | None:
    lower = text.lower()
    for keyword, objective in OBJECTIVE_KEYWORDS.items():
        if keyword in lower:
            return objective
    return None


def extract_doc_title(text: str) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("#").strip()
    return "Untitled"


def ingest():
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        client.delete_collection("criteria")
    except (ValueError, chromadb.errors.NotFoundError):
        pass

    collection = client.create_collection(
        name="criteria",
        metadata={"description": "Audit criteria: internal policies and synthetic standards"},
    )

    all_ids = []
    all_docs = []
    all_metas = []

    for filename in sorted(os.listdir(POLICIES_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(POLICIES_DIR, filename)
        with open(filepath) as f:
            text = f.read()

        doc_title = extract_doc_title(text)
        chunks = chunk_by_section(text)

        for i, chunk in enumerate(chunks):
            chunk_id = f"policy-{filename.replace('.md', '')}-{i:02d}"
            all_ids.append(chunk_id)
            all_docs.append(chunk["body"])
            all_metas.append({
                "source": doc_title,
                "source_file": filename,
                "section": chunk["section"],
                "doc_type": "policy",
            })

    for filename in sorted(os.listdir(STANDARDS_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(STANDARDS_DIR, filename)
        with open(filepath) as f:
            text = f.read()

        doc_title = extract_doc_title(text)
        chunks = chunk_by_section(text)

        for i, chunk in enumerate(chunks):
            chunk_id = f"standard-{filename.replace('.md', '')}-{i:02d}"
            meta = {
                "source": doc_title,
                "source_file": filename,
                "section": chunk["section"],
                "doc_type": "standard",
            }

            assertion = detect_assertion(chunk["body"])
            if assertion:
                meta["assertion"] = assertion

            objective = detect_objective(chunk["body"])
            if objective:
                meta["objective"] = objective

            all_ids.append(chunk_id)
            all_docs.append(chunk["body"])
            all_metas.append(meta)

    collection.add(ids=all_ids, documents=all_docs, metadatas=all_metas)

    policy_count = sum(1 for m in all_metas if m["doc_type"] == "policy")
    standard_count = sum(1 for m in all_metas if m["doc_type"] == "standard")
    print(f"Ingested {len(all_ids)} chunks into 'criteria' collection:")
    print(f"  Policies:  {policy_count} chunks")
    print(f"  Standards: {standard_count} chunks")
    print(f"Persisted to {CHROMA_PATH}")

    with_assertion = sum(1 for m in all_metas if "assertion" in m)
    with_objective = sum(1 for m in all_metas if "objective" in m)
    print(f"  Chunks with assertion tag:  {with_assertion}")
    print(f"  Chunks with objective tag:  {with_objective}")


def ingest_prior_workpapers():
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        client.delete_collection("prior_workpapers")
    except (ValueError, chromadb.errors.NotFoundError):
        pass

    collection = client.create_collection(
        name="prior_workpapers",
        metadata={"description": "Prior-year audit workpapers and findings"},
    )

    wp_path = os.path.join(DATA_DIR, "synthetic", "prior_workpapers.json")
    with open(wp_path) as f:
        workpapers = json.load(f)

    ids = []
    docs = []
    metas = []

    for wp in workpapers:
        ids.append(wp["wp_id"])
        docs.append(
            f"Objective: {wp['objective']}\n"
            f"Procedure: {wp['procedure_performed']}\n"
            f"Conclusion: {wp['conclusion']}"
        )
        metas.append({
            "wp_id": wp["wp_id"],
            "period": wp["period"],
            "objective": wp["objective"],
            "control_id": wp["control_id"],
            "conclusion": wp["conclusion"],
            "disposition": wp["disposition"],
            "deviation_rate": wp["deviation_rate"],
            "recurring_finding": wp.get("recurring_finding") or "",
        })

    collection.add(ids=ids, documents=docs, metadatas=metas)
    print(f"\nIngested {len(ids)} prior workpapers into 'prior_workpapers' collection.")


if __name__ == "__main__":
    ingest()
    ingest_prior_workpapers()
