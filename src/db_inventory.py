"""Print a compact inventory of tables and row counts."""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"


TABLE_LABELS = [
    ("trade_calendar", "交易日历"),
    ("stocks", "股票基础信息"),
    ("plates", "板块基础信息"),
    ("raw_api_responses", "接口原始返回"),
    ("limit_up_events", "涨停事件"),
    ("limit_up_plate_map", "涨停股票-板块关系"),
    ("plate_hot_rank", "涨停热门板块"),
    ("plate_daily", "板块日排名"),
    ("plate_trends", "板块趋势"),
    ("plate_reasons", "板块热门原因"),
    ("lhb_daily", "龙虎榜"),
    ("movement_alerts", "盘中异动"),
    ("market_index_daily", "大盘指数"),
    ("sentiment_daily", "市场情绪"),
    ("market_hot_daily", "市场热点"),
    ("stock_kline_daily", "个股日K"),
    ("stock_trends", "个股分时"),
    ("stock_info_snapshots", "个股资料快照"),
    ("daily_reviews", "自动复盘结论"),
    ("data_jobs", "数据任务记录"),
]


def get_inventory(db_path: str | Path = DEFAULT_DB_PATH) -> list[tuple[str, str, int]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = []
        for table, label in TABLE_LABELS:
            count = conn.execute(f"select count(*) from {table}").fetchone()[0]
            rows.append((table, label, count))
        return rows
    finally:
        conn.close()


def main() -> None:
    for table, label, count in get_inventory():
        print(f"{table}\t{label}\t{count}")


if __name__ == "__main__":
    main()
