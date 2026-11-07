from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("doc-agent")
DOCS = Path(__file__).parent / "docs"

@mcp.tool()
def search_docs(query: str, top_k: int = 3) -> list[dict]:
    """사내 문서에서 query와 관련된 문서를 찾는다."""
    results = []
    for f in DOCS.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        score = sum(text.count(w) for w in query.split())
        if score:
            results.append({"file": f.name, "score": score, "preview": text[:200]})
    return sorted(results, key=lambda r: -r["score"])[:top_k]

if __name__ == "__main__":
    mcp.run()