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

| `get_schema` | 판매 DB 테이블·컬럼 구조 조회 |
| `run_sql` | 읽기 전용 SQL 실행 (SELECT 한 문장, 결과 100행 제한) |


## Text-to-SQL 평가 결과

로컬 LLM(qwen2.5-coder:7b, CPU)으로 판매 DB 질문 15개를 실행 정확도로 측정.
모델은 고정하고, 오류 분석에 따라 컨텍스트와 실행 루프를 개선.

| 버전 | 날짜 | 바꾼 것 | 정확도 | 비고 |
|---|---|---|---|---|
| v0 | 2026-11-16 | 기본 프롬프트 (스키마만) | 10/15 (66.7%) | 값 매핑·집계 단위 오류 |
| v1 | | | | |

자세한 분석: [docs/experiments.md](docs/experiments.md)