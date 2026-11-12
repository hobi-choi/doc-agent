"""Text-to-SQL 평가 하네스 v0.

정답 SQL(gold_sql)과 예측 SQL(pred_sql)을 같은 DB에서 실행하고,
결과 행이 같으면 정답으로 친다 (execution accuracy).

사용법:
  uv run python eval/run_sql_eval.py --check                  # 정답 SQL이 전부 실행되는지 확인
  uv run python eval/run_sql_eval.py --pred eval/preds.json   # 예측 SQL 채점
preds.json 형식: {"q01": "SELECT ...", "q02": "SELECT ...", ...}
"""
import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "retail.db"
CASES_PATH = ROOT / "eval" / "sql_cases.json"


def execute(sql: str) -> list[tuple]:
    with closing(sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)) as con:
        return con.execute(sql).fetchall()


def normalize(rows: list[tuple]) -> list[tuple]:
    # 실수 오차는 소수점 둘째 자리까지만 비교
    return [tuple(round(v, 2) if isinstance(v, float) else v for v in row) for row in rows]


def same_result(gold: list[tuple], pred: list[tuple], order_matters: bool) -> bool:
    gold, pred = normalize(gold), normalize(pred)
    if order_matters:
        return gold == pred
    return Counter(gold) == Counter(pred)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="정답 SQL 실행 확인")
    parser.add_argument("--pred", type=Path, help="예측 SQL JSON 파일")
    args = parser.parse_args()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    if args.check:
        for c in cases:
            rows = execute(c["gold_sql"])
            preview = rows[:3]
            print(f"[{c['id']}|{c['level']}] {c['question']}\n    -> {len(rows)} rows, {preview}")
        return

    if not args.pred:
        parser.error("--check 또는 --pred 중 하나를 지정")

    preds = json.loads(args.pred.read_text(encoding="utf-8"))
    by_level: dict[str, list[bool]] = {}
    for c in cases:
        pred_sql = preds.get(c["id"])
        try:
            ok = pred_sql is not None and same_result(
                execute(c["gold_sql"]), execute(pred_sql), c["order_matters"]
            )
        except sqlite3.Error as e:
            ok = False
            print(f"  {c['id']} SQL 오류: {e}")
        by_level.setdefault(c["level"], []).append(ok)
        print(f"{'O' if ok else 'X'} {c['id']} {c['question']}")

    total = [ok for oks in by_level.values() for ok in oks]
    print(f"\n전체 정확도: {sum(total)}/{len(total)} ({100 * sum(total) / len(total):.1f}%)")
    for level, oks in by_level.items():
        print(f"  {level}: {sum(oks)}/{len(oks)}")


if __name__ == "__main__":
    main()