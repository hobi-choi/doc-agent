"""로컬 LLM(Ollama)으로 Text-to-SQL 예측을 만든다.

사용법:
  uv run python eval/gen_preds.py --version v0   # 스키마만
  uv run python eval/gen_preds.py --version v1   # 스키마 + 컬럼 값 힌트
  uv run python eval/gen_preds.py --version v1 --model qwen2.5-coder:3b
결과: eval/preds/<version>_<model>.json
"""
import argparse
import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import ollama

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "retail.db"
CASES_PATH = ROOT / "eval" / "sql_cases.json"
PREDS_DIR = ROOT / "eval" / "preds"

# v1: LLM에게 실제 값 목록을 알려줄 범주형 컬럼
HINT_COLUMNS = [
    ("stores", "name"),
    ("stores", "region"),
    ("stores", "channel"),
    ("products", "name"),
    ("products", "category"),
]

PROMPT = """너는 SQLite 전문가야. 아래 스키마를 보고 질문에 답하는 SQL을 한 문장만 써.
- SQLite 문법만 사용해.
- 설명 없이 SQL만 출력해.
- sale_date는 'YYYY-MM-DD' 형식의 문자열이고, 데이터는 2026년이야.

[스키마]
{schema}
{hints}
[질문]
{question}
"""


def connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def get_schema() -> str:
    with closing(connect()) as con:
        rows = con.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return "\n\n".join(r[0] for r in rows)


def get_value_hints() -> str:
    """범주형 컬럼의 실제 값 목록과 날짜 범위를 프롬프트용 텍스트로 만든다."""
    lines = ["[컬럼 값 참고]"]
    with closing(connect()) as con:
        for table, col in HINT_COLUMNS:
            values = [r[0] for r in con.execute(f"SELECT DISTINCT {col} FROM {table} ORDER BY {col}")]
            lines.append(f"- {table}.{col}: {', '.join(values)}")
        lo, hi = con.execute("SELECT MIN(sale_date), MAX(sale_date) FROM sales").fetchone()
        lines.append(f"- sales.sale_date 범위: {lo} ~ {hi}")
    return "\n".join(lines) + "\n"


def extract_sql(text: str) -> str:
    # 모델이 ```sql ... ``` 코드블록으로 감싸서 답하는 경우가 많아서 벗겨낸다
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = m.group(1) if m else text
    return sql.strip().rstrip(";").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--version", default="v1", choices=["v0", "v1"])
    args = parser.parse_args()

    schema = get_schema()
    hints = get_value_hints() if args.version == "v1" else ""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    PREDS_DIR.mkdir(parents=True, exist_ok=True)
    model_slug = re.sub(r"[^a-zA-Z0-9.]+", "-", args.model)
    out_path = PREDS_DIR / f"{args.version}_{model_slug}.json"

    preds, latencies = {}, {}
    for c in cases:
        t0 = time.time()
        res = ollama.chat(
            model=args.model,
            messages=[{"role": "user", "content": PROMPT.format(schema=schema, hints=hints, question=c["question"])}],
            options={"temperature": 0},
        )
        preds[c["id"]] = extract_sql(res.message.content)
        latencies[c["id"]] = round(time.time() - t0, 1)
        print(f"{c['id']} ({latencies[c['id']]}s): {preds[c['id']]}")

    out_path.write_text(
        json.dumps({"model": args.model, "version": args.version, "preds": preds, "latency_sec": latencies},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n저장: {out_path}")
    print(f"질문당 평균 {sum(latencies.values()) / len(latencies):.1f}초")


if __name__ == "__main__":
    main()