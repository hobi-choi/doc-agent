from pathlib import Path
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("doc-agent", instructions="사내 문서를 검색하고 조회하는 도구 모음")
DOCS = (Path(__file__).parent / "docs").resolve()


def _title(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else ""
    return first.lstrip("#").strip()


@mcp.tool()
def list_documents() -> list[dict]:
    """검색 가능한 문서의 파일명과 제목 목록을 돌려준다."""
    return [
        {"file": f.name, "title": _title(f.read_text(encoding="utf-8"))}
        for f in sorted(DOCS.glob("*.md"))
    ]


@mcp.tool()
def search_docs(query: str, top_k: int = 3) -> list[dict]:
    """query의 단어가 들어간 문서를 점수순으로 찾고, 일치한 줄을 함께 돌려준다."""
    words = query.split()
    results = []
    for f in DOCS.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        score = sum(text.count(w) for w in words)
        if score:
            hits = [line.strip() for line in text.splitlines() if any(w in line for w in words)]
            results.append({"file": f.name, "title": _title(text), "score": score, "matches": hits[:3]})
    return sorted(results, key=lambda r: -r["score"])[:top_k]


@mcp.tool()
def get_document(file: str) -> str:
    """파일명으로 문서 전체 내용을 돌려준다."""
    path = (DOCS / file).resolve()
    if path.parent != DOCS or not path.is_file():
        raise ValueError(f"문서를 찾을 수 없음: {file}")
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()