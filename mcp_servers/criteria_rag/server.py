"""MCP server: control policies and audit standards via ChromaDB RAG."""

import os
import chromadb
from mcp.server.fastmcp import FastMCP

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")

mcp = FastMCP("criteria_rag")


def _get_collection():
    if not os.path.exists(CHROMA_PATH):
        raise RuntimeError(
            f"ChromaDB store not found at {CHROMA_PATH}. "
            "Run 'python data/ingest.py' first to build the criteria collection."
        )
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        return client.get_collection("criteria")
    except Exception:
        raise RuntimeError(
            "Collection 'criteria' not found in ChromaDB. "
            "Run 'python data/ingest.py' first."
        )


@mcp.tool()
def query_criteria(query: str, source: str = "all", n_results: int = 5) -> str:
    """Semantic search over audit criteria (policies and/or standards).

    source: 'policy', 'standard', or 'all'.
    Returns top chunks with source document, section, doc_type, and assertion/objective tags.
    """
    try:
        collection = _get_collection()
    except RuntimeError as e:
        return str(e)

    where_filter = None
    if source in ("policy", "standard"):
        where_filter = {"doc_type": source}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
    )

    if not results["documents"] or not results["documents"][0]:
        return f"No criteria found for query: '{query}' (source={source})"

    lines = [f"Criteria search: '{query}' (source={source}, top {n_results})", "-" * 80]

    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        tags = []
        if "assertion" in meta:
            tags.append(f"assertion={meta['assertion']}")
        if "objective" in meta:
            tags.append(f"objective={meta['objective']}")
        tag_str = f"  [{', '.join(tags)}]" if tags else ""

        lines.append(f"\nResult {i + 1} (distance: {dist:.4f}):")
        lines.append(f"  Source:  {meta['source']}")
        lines.append(f"  Section: {meta['section']}")
        lines.append(f"  Type:    {meta['doc_type']}{tag_str}")
        lines.append(f"  Content: {doc[:300]}{'...' if len(doc) > 300 else ''}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
