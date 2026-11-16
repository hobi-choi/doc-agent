"""로컬 LLM(Ollama)으로 Text-to-SQL 예측을 만든다.

사용법:
  uv run python eval/gen_preds.py                          # 기본 모델 qwen2.5-coder:7b
  uv run python eval/gen_preds.py --model qwen2.5-coder:3b
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

PROMPT = """너는 SQLite 전문가야. 아래 스키마를 보고 질문에 답하는 SQL을 한 문장만 써.
- SQLite 문법만 사용해.
- 설명 없이 SQL만 출력해.
- sale_date는 'YYYY-MM-DD' 형식의 문자열이고, 데이터는 2026년이야.

[스키마]
{schema}

[질문]
{question}
"""


def get_schema() -> str:
    with closing(sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)) as con:
        rows = con.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return "\n\n".join(r[0] for r in rows)


def extract_sql(text: str) -> str:
    # 모델이 ```sql ... ``` 코드블록으로 감싸서 답하는 경우가 많아서 벗겨낸다
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = m.group(1) if m else text
    return sql.strip().rstrip(";").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    args = parser.parse_args()

    schema = get_schema()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    out_path = ROOT / "eval" / f"preds_{re.sub(r'[^a-zA-Z0-9]+', '_', args.model)}.json"

    preds = {}
    started = time.time()
    for c in cases:
        t0 = time.time()
        res = ollama.chat(
            model=args.model,
            messages=[{"role": "user", "content": PROMPT.format(schema=schema, question=c["question"])}],
            options={"temperature": 0},
        )
        preds[c["id"]] = extract_sql(res.message.content)
        print(f"{c['id']} ({time.time() - t0:.1f}s): {preds[c['id']]}")

    out_path.write_text(json.dumps(preds, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out_path}")
    print(f"총 {time.time() - started:.0f}초, 질문당 평균 {(time.time() - started) / len(cases):.1f}초")


if __name__ == "__main__":
    main()