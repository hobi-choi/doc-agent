# doc-agent

사내 문서 질의응답 에이전트를 위한 MCP 서버.
LLM 에이전트가 사내 문서를 검색·조회할 수 있도록 도구를 제공합니다.

## 도구
| 도구 | 설명 |
|---|---|
| `list_documents` | 문서 파일명과 제목 목록 |
| `search_docs` | 키워드 점수 기반 검색, 일치한 줄을 근거로 반환 |
| `get_document` | 문서 전체 조회 (docs 폴더 밖 접근 차단) |

## 실행
uv sync
uv run mcp dev server.py   # MCP Inspector로 테스트

## 로드맵
- [x] MCP 서버 + 기본 도구 3종
- [x] MCP Python SDK 1.x → 2.x 마이그레이션 (FastMCP → MCPServer)
- [ ] Elasticsearch BM25 + 벡터 하이브리드 검색으로 교체
- [ ] LangGraph 에이전트 연결
- [ ] 평가 하네스 (Recall@k, 답변 근거 일치율)