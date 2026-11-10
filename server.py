from pathlib import Path
from mcp.server.mcpserver import MCPServer
import re
import sqlite3
from contextlib import closing


mcp = MCPServer("doc-agent", instructions="사내 문서를 검색하고 조회하는 도구 모음")
DOCS = (Path(__file__).parent / "docs").resolve()
DB_PATH = (Path(__file__).parent / "data" / "retail.db").resolve()
MAX_ROWS = 100


def _connect_readonly() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


@mcp.tool()
def get_schema() -> str:
    """판매 DB의 테이블·컬럼 구조(CREATE 문)를 돌려준다. SQL을 쓰기 전에 먼저 호출한다."""
    with closing(_connect_readonly()) as con:
        rows = con.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return "\n\n".join(r[0] for r in rows)


@mcp.tool()
def run_sql(query: str) -> dict:
    """판매 DB에 읽기 전용 SQL(SELECT 또는 WITH로 시작하는 한 문장)을 실행하고, 결과를 최대 100행까지 돌려준다.
    실패하면 error 필드에 이유를 담아 돌려준다. 이유를 보고 SQL을 고쳐서 다시 시도한다."""
    q = query.strip().rstrip(";")
    if ";" in q:
        return {"error": "SQL은 한 문장만 실행할 수 있음"}
    if not re.match(r"(?is)^\s*(select|with)\b", q):
        return {"error": "SELECT 또는 WITH로 시작하는 조회 쿼리만 허용"}

    try:
        with closing(_connect_readonly()) as con:
            cur = con.execute(q)
            columns = [c[0] for c in cur.description]
            rows = cur.fetchmany(MAX_ROWS + 1)
    except sqlite3.Error as e:
        return {"error": f"SQL 실행 오류: {e}"}

    return {
        "columns": columns,
        "rows": [list(r) for r in rows[:MAX_ROWS]],
        "truncated": len(rows) > MAX_ROWS,
    }

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