"""从 AkShare 采集热门个股和热门板块数据

数据源：
- 热门个股：东方财富 emappdata（服务器可用）
- 行业板块：同花顺 stock_board_industry_summary_ths（服务器可用）
- 概念板块：东方财富（优先），降级到同花顺名称列表
"""

from __future__ import annotations

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MarketDB

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "market_review.db")


def resolve_hot_trade_date(db: MarketDB, trade_date: str | None = None) -> str:
    """Resolve the date used for realtime hot snapshots."""
    if trade_date:
        return trade_date
    row = db.conn.execute(
        """
        select max(trade_date) as trade_date from (
            select trade_date from trade_calendar where is_trade_day = 1
            union
            select trade_date from limit_up_events
            union
            select trade_date from market_index_daily
        )
        """
    ).fetchone()
    if row and row["trade_date"]:
        return row["trade_date"]
    raise RuntimeError("数据库里还没有交易日，无法确定热门数据归属日期")


def _fetch_hot_stocks_direct() -> list[dict]:
    """直接调用 emappdata 接口获取人气榜（绕过 push2 被封的问题）"""
    import requests

    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    payload = {
        "appId": "appId01",
        "globalId": "786e4c21-70dc-435a-93bb-38",
        "marketType": "",
        "pageNo": 1,
        "pageSize": 100,
    }
    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()

    records = []
    for item in data.get("data", []):
        sc = item.get("sc", "")  # e.g. "SZ000725" or "SH600519"
        code = sc.replace("SZ", "").replace("SH", "")
        records.append({
            "rank_no": int(item.get("rk", 0)),
            "stock_code": code,
            "stock_name": None,
            "latest_price": None,
            "change_pct": None,
            "change_amount": None,
            "amount": None,
            "turnover_rate": None,
            "source": "eastmoney_emappdata",
            "raw_payload": item,
        })
    return records


def _enrich_stocks_from_db(records: list[dict], db: MarketDB) -> list[dict]:
    """从 stocks 表补充股票名称"""
    codes = [r["stock_code"] for r in records if r.get("stock_code")]
    if not codes:
        return records
    placeholders = ",".join(["?"] * len(codes))
    rows = db.conn.execute(
        f"SELECT stock_code, stock_name FROM stocks WHERE stock_code IN ({placeholders})",
        codes,
    ).fetchall()
    name_map = {row["stock_code"]: row["stock_name"] for row in rows}
    for r in records:
        if not r.get("stock_name") and r["stock_code"] in name_map:
            r["stock_name"] = name_map[r["stock_code"]]
    return records


def _enrich_stocks_from_spot(records: list[dict]) -> list[dict]:
    """从新浪实时行情补充价格数据（push2 被封时可用）"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot()
        if df is None or df.empty:
            return records
        spot_map = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            # 新浪接口代码格式: bj920000, sh600000, sz000001
            if code.startswith(("sh", "sz", "bj")):
                code = code[2:]
            spot_map[code] = {
                "stock_name": row.get("名称"),
                "latest_price": row.get("最新价"),
                "change_pct": row.get("涨跌幅"),
                "change_amount": row.get("涨跌额"),
                "amount": row.get("成交额"),
                "turnover_rate": row.get("换手率"),
            }
        for r in records:
            code = r["stock_code"]
            if code in spot_map:
                s = spot_map[code]
                if not r.get("stock_name"):
                    r["stock_name"] = s["stock_name"]
                if r.get("latest_price") is None:
                    r["latest_price"] = s["latest_price"]
                if r.get("change_pct") is None:
                    r["change_pct"] = s["change_pct"]
                if r.get("change_amount") is None:
                    r["change_amount"] = s["change_amount"]
                if r.get("amount") is None:
                    r["amount"] = s["amount"]
                if r.get("turnover_rate") is None:
                    r["turnover_rate"] = s["turnover_rate"]
    except Exception as e:
        print(f"  ⚠️  实时行情补充失败: {e}")
    return records


def fetch_hot_stocks(db: MarketDB, trade_date: str | None = None) -> int:
    """采集东方财富人气股票排行 top 100"""
    import akshare as ak

    print("采集热门股票人气榜...")
    target_date = resolve_hot_trade_date(db, trade_date)

    # 优先尝试 AkShare 完整接口（含行情数据）
    try:
        df = ak.stock_hot_rank_em()
        if df is not None and not df.empty:
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
                    "amount": row.get("成交额"),
                    "turnover_rate": row.get("换手率"),
                    "source": "akshare.stock_hot_rank_em",
                    "raw_payload": dict(row),
                })
            count = db.import_hot_stocks(target_date, records)
            print(f"  ✅ 写入 {count} 条热门股票（含行情）")
            return count
    except Exception as e:
        print(f"  ⚠️  AkShare 完整接口不可用: {e}")

    # 降级：直接调用 emappdata（只有排名，无行情）+ 补充名称和价格
    print("  降级到 emappdata 直接接口...")
    try:
        records = _fetch_hot_stocks_direct()
        if records:
            records = _enrich_stocks_from_db(records, db)
            records = _enrich_stocks_from_spot(records)
            count = db.import_hot_stocks(target_date, records)
            print(f"  ✅ 写入 {count} 条热门股票（已补充数据）")
            return count
    except Exception as e:
        print(f"  ❌ emappdata 也不可用: {e}")

    print("  ⚠️  无数据")
    return 0


def fetch_hot_boards_industry_ths(db: MarketDB, trade_date: str | None = None) -> int:
    """采集同花顺行业板块排行（涨跌幅排序）"""
    import akshare as ak

    print("采集行业板块（同花顺）...")
    df = ak.stock_board_industry_summary_ths()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    target_date = resolve_hot_trade_date(db, trade_date)
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

    count = db.import_hot_boards(target_date, records, "industry")
    print(f"  ✅ 写入 {count} 条行业板块")
    return count


def fetch_hot_boards_concept_em(db: MarketDB, trade_date: str | None = None) -> int:
    """采集东方财富概念板块排行（push2.eastmoney.com，部分服务器不可用）"""
    import akshare as ak

    print("采集概念板块（东方财富）...")
    df = ak.stock_board_concept_name_em()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    target_date = resolve_hot_trade_date(db, trade_date)
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

    count = db.import_hot_boards(target_date, records, "concept")
    print(f"  ✅ 写入 {count} 条概念板块")
    return count


def _enrich_concept_boards_from_em(records: list[dict]) -> list[dict]:
    """尝试从东方财富概念板块补充行情数据"""
    try:
        import akshare as ak
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            return records
        em_map = {}
        for _, row in df.iterrows():
            name = row.get("板块名称", "")
            em_map[name] = {
                "latest_price": row.get("最新价"),
                "change_pct": row.get("涨跌幅"),
                "change_amount": row.get("涨跌额"),
                "up_count": row.get("上涨家数"),
                "down_count": row.get("下跌家数"),
                "leading_stock": row.get("领涨股票"),
                "leading_stock_change": row.get("领涨股票-涨跌幅"),
            }
        for r in records:
            name = r.get("board_name", "")
            if name in em_map:
                e = em_map[name]
                for key in e:
                    if r.get(key) is None:
                        r[key] = e[key]
    except Exception as e:
        print(f"  ⚠️  东方财富概念板块补充失败: {e}")
    return records


def fetch_hot_boards_concept_ths_fallback(db: MarketDB, trade_date: str | None = None) -> int:
    """降级：采集同花顺概念板块名称列表（无行情数据）"""
    import akshare as ak

    print("采集概念板块（同花顺降级，仅名称）...")
    df = ak.stock_board_concept_name_ths()
    if df is None or df.empty:
        print("  ⚠️  无数据")
        return 0

    target_date = resolve_hot_trade_date(db, trade_date)
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

    # 尝试用东方财富数据补充行情
    records = _enrich_concept_boards_from_em(records)

    count = db.import_hot_boards(target_date, records, "concept")
    print(f"  ✅ 写入 {count} 条概念板块")
    return count


def fetch_hot_boards(db: MarketDB, board_type: str = "concept", trade_date: str | None = None) -> int:
    """采集热门板块，自动选择可用数据源"""
    if board_type == "industry":
        return fetch_hot_boards_industry_ths(db, trade_date)

    # concept: 先尝试东方财富，失败则降级到同花顺
    try:
        count = fetch_hot_boards_concept_em(db, trade_date)
        if count > 0:
            return count
    except Exception as e:
        print(f"  ⚠️  东方财富概念板块不可用: {e}")

    return fetch_hot_boards_concept_ths_fallback(db, trade_date)


def main():
    parser = argparse.ArgumentParser(description="采集热门个股和热门板块快照")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite 数据库路径")
    parser.add_argument("--date", help="数据归属交易日；不传则使用数据库最新交易日")
    args = parser.parse_args()

    db = MarketDB(args.db)
    db.init_schema()
    target_date = resolve_hot_trade_date(db, args.date)
    print(f"热门数据归属日期: {target_date}")

    errors = []
    for fn, label in [
        (lambda: fetch_hot_stocks(db, target_date), "热门股票"),
        (lambda: fetch_hot_boards(db, "concept", target_date), "概念板块"),
        (lambda: fetch_hot_boards(db, "industry", target_date), "行业板块"),
    ]:
        try:
            fn()
        except Exception as e:
            print(f"❌ {label}采集失败: {e}")
            errors.append(label)

    db.close()

    if errors:
        print(f"\n⚠️  以下模块采集失败: {', '.join(errors)}")
    else:
        print(f"\n✅ 全部采集完成")
    print(f"📁 数据库: {args.db}")


if __name__ == "__main__":
    main()
