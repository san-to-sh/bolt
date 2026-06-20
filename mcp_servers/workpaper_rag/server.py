"""MCP server: prior-year workpapers and findings for precedent via ChromaDB RAG."""

import os
import chromadb
from mcp.server.fastmcp import FastMCP

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")

mcp = FastMCP("workpaper_rag")


def _get_collection():
    if not os.path.exists(CHROMA_PATH):
        raise RuntimeError(
            f"ChromaDB store not found at {CHROMA_PATH}. "
            "Run 'python data/ingest.py' first to build the prior_workpapers collection."
        )
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        return client.get_collection("prior_workpapers")
    except Exception:
        raise RuntimeError(
            "Collection 'prior_workpapers' not found in ChromaDB. "
            "Run 'python data/ingest.py' first."
        )


@mcp.tool()
def query_prior_workpapers(query: str, n_results: int = 3) -> str:
    """Search prior-year workpapers for precedent.

    Returns top 3 prior workpapers with objective, conclusion, disposition,
    deviation_rate, and recurring_finding note.
    """
    try:
        collection = _get_collection()
    except RuntimeError as e:
        return str(e)

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    if not results["documents"] or not results["documents"][0]:
        return f"No prior workpapers found for query: '{query}'"

    lines = [f"Prior workpaper search: '{query}' (top {n_results})", "-" * 80]

    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        recurring = meta.get("recurring_finding", "")
        recurring_str = recurring if recurring else "(none)"

        lines.append(f"\nResult {i + 1} (distance: {dist:.4f}):")
        lines.append(f"  WP ID:        {meta['wp_id']}")
        lines.append(f"  Period:       {meta['period']}")
        lines.append(f"  Control:      {meta['control_id']}")
        lines.append(f"  Objective:    {meta['objective']}")
        lines.append(f"  Disposition:  {meta['disposition']}")
        lines.append(f"  Dev. Rate:    {meta['deviation_rate']}")
        lines.append(f"  Conclusion:   {meta['conclusion']}")
        lines.append(f"  Recurring:    {recurring_str}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
