"""从 AkShare 采集热门个股和热门板块数据

数据源：
- 热门个股：东方财富 emappdata（服务器可用）
- 行业板块：同花顺 stock_board_industry_summary_ths（服务器可用）
- 概念板块：东方财富（优先），降级到同花顺名称列表
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MarketDB

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "market_review.db")


def fetch_hot_stocks(db: MarketDB) -> int:
    """采集东方财富人气股票排行 top 100"""
    import akshare as ak

    print("采集热门股票人气榜...")
    df = ak.stock_hot_rank_em()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for _, row in df.iterrows():
        code = str(row.get("代码", "")).replace("SZ", "").replace("SH", "")
        records.append({
            "rank_no": int(row["当前排名"]),
            "stock_code": code,
            "stock_name": row.get("股票名称"),
            "latest_price": row.get("最新价"),
            "change_pct": row.get("涨跌幅"),
            "change_amount": row.get("涨跌额"),
        })

    count = db.import_hot_stocks(today, records)
    print(f"  ✅ 写入 {count} 条热门股票")
    return count


def fetch_hot_boards_industry_ths(db: MarketDB) -> int:
    """采集同花顺行业板块排行（涨跌幅排序）"""
    import akshare as ak

    print("采集行业板块（同花顺）...")
    df = ak.stock_board_industry_summary_ths()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for idx, row in df.iterrows():
        records.append({
            "rank_no": idx + 1,
            "board_code": "",
            "board_name": row.get("板块"),
            "latest_price": row.get("均价"),
            "change_pct": row.get("涨跌幅"),
            "change_amount": None,
            "total_market_cap": None,
            "turnover_rate": None,
            "up_count": row.get("上涨家数"),
            "down_count": row.get("下跌家数"),
            "leading_stock": row.get("领涨股"),
            "leading_stock_change": row.get("领涨股-涨跌幅"),
        })

    count = db.import_hot_boards(today, records, "industry")
    print(f"  ✅ 写入 {count} 条行业板块")
    return count


def fetch_hot_boards_concept_em(db: MarketDB) -> int:
    """采集东方财富概念板块排行（push2.eastmoney.com，部分服务器不可用）"""
    import akshare as ak

    print("采集概念板块（东方财富）...")
    df = ak.stock_board_concept_name_em()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for _, row in df.iterrows():
        records.append({
            "rank_no": int(row["排名"]),
            "board_code": str(row.get("板块代码", "")),
            "board_name": row.get("板块名称"),
            "latest_price": row.get("最新价"),
            "change_pct": row.get("涨跌幅"),
            "change_amount": row.get("涨跌额"),
            "total_market_cap": row.get("总市值"),
            "turnover_rate": row.get("换手率"),
            "up_count": row.get("上涨家数"),
            "down_count": row.get("下跌家数"),
            "leading_stock": row.get("领涨股票"),
            "leading_stock_change": row.get("领涨股票-涨跌幅"),
        })

    count = db.import_hot_boards(today, records, "concept")
    print(f"  ✅ 写入 {count} 条概念板块")
    return count


def fetch_hot_boards_concept_ths_fallback(db: MarketDB) -> int:
    """降级：采集同花顺概念板块名称列表（无行情数据）"""
    import akshare as ak

    print("采集概念板块（同花顺降级，仅名称）...")
    df = ak.stock_board_concept_name_ths()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for idx, row in df.iterrows():
        records.append({
            "rank_no": idx + 1,
            "board_code": str(row.get("code", "")),
            "board_name": row.get("name"),
            "latest_price": None,
            "change_pct": None,
            "change_amount": None,
            "total_market_cap": None,
            "turnover_rate": None,
            "up_count": None,
            "down_count": None,
            "leading_stock": None,
            "leading_stock_change": None,
        })

    count = db.import_hot_boards(today, records, "concept")
    print(f"  ✅ 写入 {count} 条概念板块（仅名称）")
    return count


def fetch_hot_boards(db: MarketDB, board_type: str = "concept") -> int:
    """采集热门板块，自动选择可用数据源"""
    if board_type == "industry":
        return fetch_hot_boards_industry_ths(db)

    # concept: 先尝试东方财富，失败则降级到同花顺
    try:
        count = fetch_hot_boards_concept_em(db)
        if count > 0:
            return count
    except Exception as e:
        print(f"  ⚠️  东方财富概念板块不可用: {e}")

    return fetch_hot_boards_concept_ths_fallback(db)


def main():
    db = MarketDB(DEFAULT_DB_PATH)
    db.init_schema()

    try:
        fetch_hot_stocks(db)
        fetch_hot_boards(db, "concept")
        fetch_hot_boards(db, "industry")
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print(f"\n📁 数据库: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    main()
