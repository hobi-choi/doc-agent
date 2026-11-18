"""Text-to-SQL 평가 하네스.

정답 SQL(gold_sql)과 예측 SQL을 같은 DB에서 실행하고,
결과 행이 같으면 정답으로 친다 (execution accuracy).

사용법:
  uv run python eval/run_sql_eval.py --check                                 # 정답 SQL 실행 확인
  uv run python eval/run_sql_eval.py --pred eval/preds/v1_qwen2.5-coder-7b.json
결과: 화면에 요약 출력 + eval/results/<예측 파일 이름>.csv 저장
"""
import argparse
import csv
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "retail.db"
CASES_PATH = ROOT / "eval" / "sql_cases.json"
RESULTS_DIR = ROOT / "eval" / "results"


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


def load_preds(path: Path) -> tuple[dict, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "preds" in data:  # gen_preds.py 새 형식
        return data["preds"], data.get("latency_sec", {})
    return data, {}  # 예전 형식: {"q01": "SELECT ...", ...}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="정답 SQL 실행 확인")
    parser.add_argument("--pred", type=Path, help="예측 SQL JSON 파일")
    args = parser.parse_args()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    if args.check:
        for c in cases:
            rows = execute(c["gold_sql"])
            print(f"[{c['id']}|{c['level']}] {c['question']}\n    -> {len(rows)} rows, {rows[:3]}")
        return
    if not args.pred:
        parser.error("--check 또는 --pred 중 하나를 지정")

    preds, latencies = load_preds(args.pred)
    records, by_level = [], {}
    for c in cases:
        pred_sql = preds.get(c["id"], "")
        error = ""
        try:
            ok = bool(pred_sql) and same_result(execute(c["gold_sql"]), execute(pred_sql), c["order_matters"])
        except sqlite3.Error as e:
            ok, error = False, str(e)
        by_level.setdefault(c["level"], []).append(ok)
        records.append({
            "id": c["id"], "level": c["level"], "question": c["question"], "correct": "O" if ok else "X",
            "error": error, "latency_sec": latencies.get(c["id"], ""),
            "gold_sql": c["gold_sql"], "pred_sql": pred_sql,
        })
        print(f"{'O' if ok else 'X'} {c['id']} {c['question']}" + (f"  [SQL 오류: {error}]" if error else ""))

    total = [ok for oks in by_level.values() for ok in oks]
    print(f"\n전체 정확도: {sum(total)}/{len(total)} ({100 * sum(total) / len(total):.1f}%)")
    for level, oks in by_level.items():
        print(f"  {level}: {sum(oks)}/{len(oks)}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{args.pred.stem}.csv"
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: 엑셀에서 한글 안 깨지게
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()