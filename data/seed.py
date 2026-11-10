import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).parent / "retail.db"
random.seed(42)

STORES = [
    (1, "강남점", "서울", "오프라인"),
    (2, "홍대점", "서울", "오프라인"),
    (3, "부산점", "부산", "오프라인"),
    (4, "공식몰", "온라인", "온라인"),
]
PRODUCTS = [
    (1, "숏 패딩", "아우터", 329000),
    (2, "경량 패딩 조끼", "아우터", 159000),
    (3, "플리스 자켓", "아우터", 189000),
    (4, "로고 반팔 티셔츠", "상의", 49000),
    (5, "맨투맨", "상의", 89000),
    (6, "트레킹화", "신발", 199000),
    (7, "방한 부츠", "신발", 229000),
    (8, "백팩 30L", "가방", 139000),
]
WINTER_ITEMS = {1, 2, 3, 7}
SUMMER_ITEMS = {4}


def main():
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE stores (
        store_id INTEGER PRIMARY KEY,
        name     TEXT,   -- 매장명
        region   TEXT,   -- 지역
        channel  TEXT    -- 오프라인 / 온라인
    );
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        name       TEXT,    -- 상품명
        category   TEXT,    -- 아우터, 상의, 신발, 가방
        price      INTEGER  -- 정가(원)
    );
    CREATE TABLE sales (
        sale_id    INTEGER PRIMARY KEY,
        sale_date  TEXT,     -- YYYY-MM-DD
        store_id   INTEGER REFERENCES stores(store_id),
        product_id INTEGER REFERENCES products(product_id),
        quantity   INTEGER,  -- 판매 수량
        amount     INTEGER   -- 판매 금액(원)
    );
    """)
    con.executemany("INSERT INTO stores VALUES (?, ?, ?, ?)", STORES)
    con.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", PRODUCTS)

    rows = []
    d = date(2026, 1, 1)
    while d <= date(2026, 10, 31):
        winter = d.month in (1, 2, 10)
        summer = d.month in (6, 7, 8)
        for store_id, *_ in STORES:
            for product_id, _, _, price in PRODUCTS:
                weight = 1
                if winter and product_id in WINTER_ITEMS:
                    weight = 3
                if summer and product_id in SUMMER_ITEMS:
                    weight = 3
                qty = random.randint(0, weight * 2)
                if qty:
                    rows.append((d.isoformat(), store_id, product_id, qty, qty * price))
        d += timedelta(days=1)

    con.executemany(
        "INSERT INTO sales (sale_date, store_id, product_id, quantity, amount) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    con.commit()
    con.close()
    print(f"sales rows: {len(rows)}")


if __name__ == "__main__":
    main()