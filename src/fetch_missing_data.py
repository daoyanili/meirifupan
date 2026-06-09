"""Fill missing review datasets with AkShare-backed collectors."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MarketDB


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "market_review.db")


MOVEMENT_TYPES = [
    "大笔买入",
    "大笔卖出",
    "火箭发射",
    "高台跳水",
    "快速反弹",
    "封涨停板",
    "打开涨停板",
    "封跌停板",
    "打开跌停板",
]

INDEX_SYMBOLS = {
    "sh000001": ("000001.SS", "上证指数"),
    "sz399001": ("399001.SZ", "深证成指"),
    "sz399006": ("399006.SZ", "创业板指"),
    "bj899050": ("899050.BJ", "北证50"),
}


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        return value != value
    except Exception:
        return False


def _clean(value: Any) -> Any:
    if _is_blank(value):
        return None
    if hasattr(value, "item"):
        try:
            return _clean(value.item())
        except Exception:
            pass
    return value


def _num(value: Any) -> float | None:
    value = _clean(value)
    if value in ("", "-", "--", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    value = _num(value)
    return int(value) if value is not None else None


def _text(value: Any) -> str | None:
    value = _clean(value)
    if value is None:
        return None
    return str(value)


def _stock_code(value: Any) -> str:
    code = str(value or "").strip()
    if code.lower().startswith(("sh", "sz", "bj")):
        code = code[2:]
    return code.upper()


def _compact_time(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if len(text) == 6 and text.isdigit():
        return f"{text[:2]}:{text[2:4]}:{text[4:]}"
    return text


def _date_for_akshare(date: str) -> str:
    return date.replace("-", "")


def get_default_date(db: MarketDB) -> str:
    row = db.conn.execute(
        """
        select max(trade_date) as trade_date from (
            select trade_date from trade_calendar
            union
            select trade_date from limit_up_events
            union
            select trade_date from plate_hot_rank
            union
            select trade_date from market_breadth_daily
            union
            select trade_date from lhb_daily
        )
        """
    ).fetchone()
    if row and row["trade_date"]:
        return row["trade_date"]
    return datetime.now().strftime("%Y-%m-%d")


def dataframe_records(df: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in df.to_dict(orient="records")]


def fetch_spot_snapshot() -> Any:
    import akshare as ak

    return ak.stock_zh_a_spot()


def import_market_breadth_and_hot_stocks(db: MarketDB, trade_date: str, spot_df: Any | None = None) -> tuple[int, int]:
    if spot_df is None:
        spot_df = fetch_spot_snapshot()
    if spot_df is None or spot_df.empty:
        return 0, 0

    change = spot_df["涨跌幅"].apply(_num)
    amount = spot_df["成交额"].apply(_num)
    valid_change = change.dropna()
    snapshot = {
        "trade_date": trade_date,
        "total_count": int(valid_change.count()),
        "up_count": int((change > 0).sum()),
        "down_count": int((change < 0).sum()),
        "flat_count": int((change == 0).sum()),
        "limit_up_count": int((change >= 9.8).sum()),
        "limit_down_count": int((change <= -9.8).sum()),
        "natural_limit_up_count": int((change >= 9.8).sum()),
        "natural_limit_down_count": int((change <= -9.8).sum()),
        "avg_change_pct": round(float(valid_change.mean()), 2) if not valid_change.empty else None,
        "amount": float(amount.dropna().sum()),
        "source": "akshare.stock_zh_a_spot",
    }
    breadth_count = db.import_market_breadth(trade_date, snapshot)

    ranked = spot_df.copy()
    ranked["_amount"] = ranked["成交额"].apply(_num)
    ranked = ranked.sort_values("_amount", ascending=False).head(100)
    hot_records = []
    for rank_no, row in enumerate(dataframe_records(ranked), start=1):
        hot_records.append({
            "rank_no": rank_no,
            "stock_code": _stock_code(row.get("代码")),
            "stock_name": _text(row.get("名称")),
            "latest_price": _num(row.get("最新价")),
            "change_pct": _num(row.get("涨跌幅")),
            "change_amount": _num(row.get("涨跌额")),
            "amount": _num(row.get("成交额")),
            "turnover_rate": _num(row.get("换手率")),
            "source": "spot_amount_rank",
            "raw_payload": row,
        })
    hot_count = db.import_hot_stocks(trade_date, hot_records)
    return breadth_count, hot_count


def fetch_limit_down_records(trade_date: str) -> list[dict[str, Any]]:
    import akshare as ak

    df = ak.stock_zt_pool_dtgc_em(date=_date_for_akshare(trade_date))
    records = []
    for row in dataframe_records(df):
        records.append({
            "stock_code": _stock_code(row.get("代码")),
            "stock_name": _text(row.get("名称")),
            "latest_price": _num(row.get("最新价")),
            "change_pct": _num(row.get("涨跌幅")),
            "amount": _num(row.get("成交额")),
            "circulation_value": _num(row.get("流通市值")),
            "total_market_cap": _num(row.get("总市值")),
            "turnover_rate": _num(row.get("换手率")),
            "seal_amount": _num(row.get("封单资金")),
            "last_limit_down_time": _compact_time(row.get("最后封板时间")),
            "limit_down_days": _int(row.get("连续跌停")),
            "open_count": _int(row.get("开板次数")),
            "industry": _text(row.get("所属行业")),
            "raw": row,
        })
    return records


def fetch_broken_limit_up_records(trade_date: str) -> list[dict[str, Any]]:
    import akshare as ak

    df = ak.stock_zt_pool_zbgc_em(date=_date_for_akshare(trade_date))
    records = []
    for row in dataframe_records(df):
        records.append({
            "stock_code": _stock_code(row.get("代码")),
            "stock_name": _text(row.get("名称")),
            "latest_price": _num(row.get("最新价")),
            "change_pct": _num(row.get("涨跌幅")),
            "limit_up_price": _num(row.get("涨停价")),
            "amount": _num(row.get("成交额")),
            "circulation_value": _num(row.get("流通市值")),
            "total_market_cap": _num(row.get("总市值")),
            "turnover_rate": _num(row.get("换手率")),
            "first_limit_up_time": _compact_time(row.get("首次封板时间")),
            "open_count": _int(row.get("炸板次数")),
            "limit_up_stat": _text(row.get("涨停统计")),
            "amplitude": _num(row.get("振幅")),
            "industry": _text(row.get("所属行业")),
            "raw": row,
        })
    return records


def fetch_lhb_records(trade_date: str) -> list[dict[str, Any]]:
    import akshare as ak

    date_arg = _date_for_akshare(trade_date)
    df = ak.stock_lhb_detail_em(start_date=date_arg, end_date=date_arg)
    records = []
    for row in dataframe_records(df):
        records.append({
            "stock_code": _stock_code(row.get("代码")),
            "stock_name": _text(row.get("名称")),
            "reason": _text(row.get("上榜原因")),
            "buy_amount": _num(row.get("龙虎榜买入额")),
            "sell_amount": _num(row.get("龙虎榜卖出额")),
            "net_buy_amount": _num(row.get("龙虎榜净买额")),
            "close_price": _num(row.get("收盘价")),
            "change_pct": _num(row.get("涨跌幅")),
            "turnover_rate": _num(row.get("换手率")),
            "raw": row,
        })
    return records


def fetch_index_daily_records(trade_date: str) -> list[dict[str, Any]]:
    import akshare as ak

    records = []
    for symbol, (index_code, index_name) in INDEX_SYMBOLS.items():
        df = ak.stock_zh_index_daily(symbol=symbol)
        if df is None or df.empty:
            continue
        matched = df[df["date"].astype(str) == trade_date]
        if matched.empty:
            continue
        row = dataframe_records(matched.tail(1))[0]
        close_price = _num(row.get("close"))
        prev_df = df[df["date"].astype(str) < trade_date].tail(1)
        change_pct = None
        if close_price is not None and not prev_df.empty:
            prev_close = _num(dataframe_records(prev_df)[0].get("close"))
            if prev_close:
                change_pct = round((close_price - prev_close) / prev_close * 100, 2)
        records.append({
            "code": index_code,
            "name": index_name,
            "last_px": close_price,
            "px_change_rate": change_pct,
            "amount": _num(row.get("volume")),
            "open": _num(row.get("open")),
            "high": _num(row.get("high")),
            "low": _num(row.get("low")),
            "source_symbol": symbol,
            "raw": row,
        })
    return records


def fetch_market_hot_records() -> list[dict[str, Any]]:
    import akshare as ak

    df = ak.stock_board_change_em()
    df = df.sort_values("板块异动总次数", ascending=False).head(100)
    records = []
    for rank_no, row in enumerate(dataframe_records(df), start=1):
        name = _text(row.get("板块名称"))
        if not name:
            continue
        records.append({
            "item_key": name,
            "item_name": name,
            "score": _num(row.get("板块异动总次数")),
            "rank_no": rank_no,
            "change_pct": _num(row.get("涨跌幅")),
            "main_net_inflow": _num(row.get("主力净流入")),
            "leading_stock_code": _stock_code(row.get("板块异动最频繁个股及所属类型-股票代码")),
            "leading_stock_name": _text(row.get("板块异动最频繁个股及所属类型-股票名称")),
            "leading_type": _text(row.get("板块异动最频繁个股及所属类型-买卖方向")),
            "raw": row,
        })
    return records


def _parse_change_info(info: Any) -> tuple[float | None, float | None, float | None]:
    parts = str(info or "").split(",")
    if len(parts) < 4:
        return None, None, None
    price = _num(parts[1])
    change_pct = _num(parts[2])
    amount = _num(parts[3])
    if change_pct is not None and abs(change_pct) < 1:
        change_pct = change_pct * 100
    return price, change_pct, amount


def fetch_movement_records(limit_per_type: int = 80) -> list[dict[str, Any]]:
    import akshare as ak

    records = []
    seen: set[tuple[str, str, str]] = set()
    for movement_type in MOVEMENT_TYPES:
        try:
            df = ak.stock_changes_em(symbol=movement_type)
        except Exception as exc:
            print(f"  movement {movement_type} failed: {exc}")
            continue
        for row in dataframe_records(df.head(limit_per_type)):
            stock_code = _stock_code(row.get("代码"))
            alert_time = _text(row.get("时间"))
            if not stock_code or not alert_time:
                continue
            key = (movement_type, alert_time, stock_code)
            if key in seen:
                continue
            seen.add(key)
            price, change_pct, amount = _parse_change_info(row.get("相关信息"))
            records.append({
                "alert_time": alert_time,
                "stock_code": stock_code,
                "stock_name": _text(row.get("名称")),
                "alert_type": movement_type,
                "alert_text": _text(row.get("板块")),
                "price": price,
                "change_pct": change_pct,
                "amount": amount,
                "raw": row,
            })
    return records


def select_kline_stock_codes(db: MarketDB, trade_date: str, limit: int) -> list[str]:
    rows = db.conn.execute(
        """
        select stock_code from (
            select stock_code, coalesce(up_limit_keep_times, 0) as level, coalesce(fengdan_money, 0) as amount
            from limit_up_events
            where trade_date <= ?
            order by trade_date desc, level desc, amount desc
            limit ?
        )
        union
        select stock_code from (
            select stock_code from lhb_daily
            where trade_date = ?
            order by abs(coalesce(net_buy_amount, 0)) desc
            limit ?
        )
        union
        select stock_code from (
            select stock_code from hot_stocks
            where trade_date = ?
            order by rank_no
            limit ?
        )
        """,
        (trade_date, limit, trade_date, max(5, limit // 3), trade_date, max(5, limit // 3)),
    ).fetchall()
    codes = []
    for row in rows:
        code = row["stock_code"]
        if code and code not in codes:
            codes.append(code)
    return codes[:limit]


def fetch_stock_kline_records(stock_code: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
    import akshare as ak

    start = _date_for_akshare(start_date)
    end = _date_for_akshare(end_date)
    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="",
        )
    except Exception:
        prefix = "sh" if stock_code.startswith(("6", "9")) else "sz"
        df = ak.stock_zh_a_daily(
            symbol=f"{prefix}{stock_code}",
            start_date=start,
            end_date=end,
            adjust="",
        )
    records = []
    for row in dataframe_records(df):
        trade_date = _text(row.get("日期") or row.get("date"))
        if not trade_date:
            continue
        records.append({
            "trade_date": trade_date,
            "open_price": _num(row.get("开盘") or row.get("open")),
            "high_price": _num(row.get("最高") or row.get("high")),
            "low_price": _num(row.get("最低") or row.get("low")),
            "close_price": _num(row.get("收盘") or row.get("close")),
            "volume": _num(row.get("成交量") or row.get("volume")),
            "amount": _num(row.get("成交额") or row.get("amount")),
            "change_pct": _num(row.get("涨跌幅")),
            "raw": row,
        })
    return records


def run_collectors(
    trade_date: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
    kline_limit: int = 30,
    include_realtime: bool = True,
    include_historical: bool = True,
) -> dict[str, int]:
    db = MarketDB(db_path)
    db.init_schema()
    if trade_date is None:
        trade_date = get_default_date(db)
    print(f"补数据日期: {trade_date}")

    results: dict[str, int] = {}
    try:
        if include_realtime:
            try:
                breadth_count, hot_count = import_market_breadth_and_hot_stocks(db, trade_date)
                results["market_breadth_daily"] = breadth_count
                results["hot_stocks"] = hot_count
                print(f"  market breadth: {breadth_count}, hot stocks: {hot_count}")
            except Exception as exc:
                print(f"  market breadth / hot stocks failed: {exc}")

        if include_historical:
            try:
                records = fetch_index_daily_records(trade_date)
                results["market_index_daily"] = db.import_index_daily(trade_date, records, raw_source="akshare.stock_zh_index_daily")
                print(f"  market index: {results['market_index_daily']}")
            except Exception as exc:
                print(f"  market index failed: {exc}")

            try:
                records = fetch_limit_down_records(trade_date)
                results["limit_down_events"] = db.import_limit_down_events(trade_date, records)
                print(f"  limit down: {results['limit_down_events']}")
            except Exception as exc:
                print(f"  limit down failed: {exc}")

            try:
                records = fetch_broken_limit_up_records(trade_date)
                results["broken_limit_up_events"] = db.import_broken_limit_up_events(trade_date, records)
                print(f"  broken limit up: {results['broken_limit_up_events']}")
            except Exception as exc:
                print(f"  broken limit up failed: {exc}")

            try:
                records = fetch_lhb_records(trade_date)
                results["lhb_daily"] = db.import_lhb_daily(trade_date, records)
                print(f"  lhb: {results['lhb_daily']}")
            except Exception as exc:
                print(f"  lhb failed: {exc}")

        if include_realtime:
            try:
                records = fetch_market_hot_records()
                results["market_hot_daily"] = db.import_market_hot_daily(trade_date, records)
                print(f"  market hot: {results['market_hot_daily']}")
            except Exception as exc:
                print(f"  market hot failed: {exc}")

            try:
                records = fetch_movement_records()
                results["movement_alerts"] = db.import_movement_alerts(trade_date, records)
                print(f"  movement alerts: {results['movement_alerts']}")
            except Exception as exc:
                print(f"  movement alerts failed: {exc}")

        if include_historical and kline_limit > 0:
            codes = select_kline_stock_codes(db, trade_date, kline_limit)
            kline_count = 0
            for code in codes:
                try:
                    records = fetch_stock_kline_records(code, trade_date, trade_date)
                    kline_count += db.import_stock_kline_daily(code, records)
                except Exception as exc:
                    print(f"  kline {code} failed: {exc}")
            results["stock_kline_daily"] = kline_count
            print(f"  stock kline: {kline_count} rows for {len(codes)} stocks")
    finally:
        db.close()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="补齐 A 股复盘缺失数据")
    parser.add_argument("--date", help="交易日期，格式 YYYY-MM-DD；不传则使用数据库最新交易日")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite 数据库路径")
    parser.add_argument("--kline-limit", type=int, default=30, help="补多少只核心股票的日 K，0 表示跳过")
    parser.add_argument("--historical-only", action="store_true", help="只补可按日期回补的数据")
    parser.add_argument("--realtime-only", action="store_true", help="只补实时口径数据")
    args = parser.parse_args()

    include_realtime = not args.historical_only
    include_historical = not args.realtime_only
    run_collectors(
        args.date,
        args.db,
        args.kline_limit,
        include_realtime,
        include_historical,
    )


if __name__ == "__main__":
    main()
