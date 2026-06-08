"""Fetch real board index daily K-line data from THS."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MarketDB


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"

PLATE_NAME_ALIASES = {
    "一季报增长": "2026一季报预增",
    "业绩增长": "2026一季报预增",
    "低价股": "",
    "芯片": "芯片概念",
    "股权转让": "股权转让(并购重组)",
    "年报增长": "2025年报预增",
    "新材料概念": "金属新材料",
    "地产链": "房地产",
    "金融概念": "多元金融",
}


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _clean(value: Any) -> Any:
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        pass
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


def _date_for_api(date_text: str) -> str:
    return date_text.replace("-", "")


def _window_start(end_date: str, calendar_days: int = 45) -> str:
    dt = datetime.strptime(end_date, "%Y-%m-%d")
    return (dt - timedelta(days=calendar_days)).strftime("%Y%m%d")


def _normalize_name(value: str) -> str:
    return (
        str(value or "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("概念", "")
        .replace("板块", "")
        .replace("产业链", "")
        .replace("链", "")
        .replace("类", "")
        .replace(" ", "")
        .replace("　", "")
        .lower()
    )


def _unique_name_match(candidates: list[str], names: set[str]) -> str | None:
    norm_candidates = [_normalize_name(candidate) for candidate in candidates if candidate]
    matches = []
    for name in names:
        normalized = _normalize_name(name)
        if any(candidate and (candidate in normalized or normalized in candidate) for candidate in norm_candidates):
            matches.append(name)
    return matches[0] if len(matches) == 1 else None


def resolve_ths_symbol(
    plate_name: str,
    concept_names: set[str],
    industry_names: set[str],
) -> tuple[str, str] | None:
    alias = PLATE_NAME_ALIASES.get(plate_name, plate_name)
    if not alias:
        return None
    candidates = [alias, plate_name, f"{plate_name}概念"]
    for candidate in candidates:
        if candidate in concept_names:
            return "concept", candidate
        if candidate in industry_names:
            return "industry", candidate

    concept_match = _unique_name_match(candidates, concept_names)
    if concept_match:
        return "concept", concept_match
    industry_match = _unique_name_match(candidates, industry_names)
    if industry_match:
        return "industry", industry_match
    return None


def load_ths_board_names() -> tuple[set[str], set[str]]:
    import akshare as ak

    concept_df = ak.stock_board_concept_name_ths()
    industry_df = ak.stock_board_industry_name_ths()
    concept_names = set(concept_df["name"].dropna().astype(str).tolist()) if concept_df is not None else set()
    industry_names = set(industry_df["name"].dropna().astype(str).tolist()) if industry_df is not None else set()
    return concept_names, industry_names


def get_recent_core_plates(
    db_path: str | Path = DEFAULT_DB_PATH,
    end_date: str | None = None,
    review_days: int = 20,
    per_day_limit: int = 8,
) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    try:
        if end_date is None:
            row = conn.execute("select max(trade_date) as trade_date from limit_up_events").fetchone()
            end_date = row["trade_date"] if row and row["trade_date"] else None
        if not end_date:
            return []
        date_rows = conn.execute(
            """
            select distinct trade_date
            from limit_up_events
            where trade_date <= ?
            order by trade_date desc
            limit ?
            """,
            (end_date, review_days),
        ).fetchall()
        dates = [row["trade_date"] for row in date_rows]
        if not dates:
            return []
        placeholders = ",".join(["?"] * len(dates))
        rows = conn.execute(
            f"""
            select plate_code, plate_name, count(distinct trade_date) as active_days,
                   count(distinct trade_date || ':' || stock_code) as total_limit_up_count
            from limit_up_plate_map
            where trade_date in ({placeholders})
            group by plate_code, plate_name
            order by active_days desc, total_limit_up_count desc
            limit ?
            """,
            (*dates, per_day_limit * 4),
        ).fetchall()
        plates: dict[str, dict[str, Any]] = {str(row["plate_code"]): dict(row) for row in rows}
        hot_rows = conn.execute(
            f"""
            select plate_code, plate_name,
                   count(distinct trade_date) as hot_days,
                   min(rank_no) as best_rank,
                   max(score) as best_score
            from plate_hot_rank
            where trade_date in ({placeholders}) and source = 'uplimit_hot'
            group by plate_code, plate_name
            order by hot_days desc, best_rank asc, best_score desc
            limit ?
            """,
            (*dates, per_day_limit * 4),
        ).fetchall()
        for row in hot_rows:
            plate_code = str(row["plate_code"])
            if plate_code in plates:
                plates[plate_code]["hot_days"] = row["hot_days"]
                plates[plate_code]["best_rank"] = row["best_rank"]
                continue
            plates[plate_code] = {
                "plate_code": plate_code,
                "plate_name": row["plate_name"],
                "active_days": 0,
                "total_limit_up_count": 0,
                "hot_days": row["hot_days"],
                "best_rank": row["best_rank"],
                "best_score": row["best_score"],
            }
        return sorted(
            plates.values(),
            key=lambda plate: (
                -int(plate.get("hot_days") or 0),
                int(plate.get("best_rank") or 999999),
                -int(plate.get("active_days") or 0),
                -int(plate.get("total_limit_up_count") or 0),
            ),
        )
    finally:
        conn.close()


def _records_from_ths_frame(
    df: Any,
    plate: dict[str, Any],
    board_type: str,
    source: str,
    end_date: str,
    matched_name: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if df is None or df.empty:
        return records
    prev_close: float | None = None
    for row in df.to_dict(orient="records"):
        trade_date = str(row.get("日期") or "")
        if not trade_date or trade_date > end_date:
            continue
        close_price = _num(row.get("收盘价"))
        change_pct = None
        if prev_close and close_price is not None:
            change_pct = round((close_price - prev_close) / prev_close * 100, 2)
        prev_close = close_price if close_price is not None else prev_close
        records.append(
            {
                "plate_code": str(plate.get("plate_code") or plate.get("plate_name")),
                "plate_name": plate.get("plate_name"),
                "board_type": board_type,
                "source": source,
                "trade_date": trade_date,
                "open_price": _num(row.get("开盘价")),
                "high_price": _num(row.get("最高价")),
                "low_price": _num(row.get("最低价")),
                "close_price": close_price,
                "change_pct": change_pct,
                "volume": _num(row.get("成交量")),
                "amount": _num(row.get("成交额")),
                "raw_payload": {
                    "matched_name": matched_name,
                    "board_type": board_type,
                    "source": source,
                    "row": row,
                },
            }
        )
    return records


def fetch_plate_index_records(
    plate: dict[str, Any],
    start_date: str,
    end_date: str,
    concept_names: set[str] | None = None,
    industry_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    import akshare as ak

    plate_name = str(plate.get("plate_name") or "")
    if not plate_name:
        return []
    if concept_names is None or industry_names is None:
        concept_names, industry_names = load_ths_board_names()
    resolved = resolve_ths_symbol(plate_name, concept_names, industry_names)
    if not resolved:
        print(f"  跳过 {plate_name}: 未匹配到同花顺板块指数名称")
        return []
    resolved_type, symbol = resolved

    errors: list[str] = []
    fetch_plan = [
        (
            resolved_type,
            f"ths_{resolved_type}_index",
            ak.stock_board_concept_index_ths if resolved_type == "concept" else ak.stock_board_industry_index_ths,
            {"symbol": symbol, "start_date": start_date, "end_date": _date_for_api(end_date)},
        )
    ]
    for board_type, source, fetcher, kwargs in fetch_plan:
        try:
            df = fetcher(**kwargs)
            records = _records_from_ths_frame(df, plate, board_type, source, end_date, symbol)
            if records:
                return records
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    if errors:
        print(f"  跳过 {plate_name}: {' | '.join(errors[:2])}")
    return []


def fetch_plate_index_daily(
    db_path: str | Path = DEFAULT_DB_PATH,
    end_date: str | None = None,
    review_days: int = 20,
    per_day_limit: int = 8,
) -> dict[str, int]:
    plates = get_recent_core_plates(db_path, end_date=end_date, review_days=review_days, per_day_limit=per_day_limit)
    if not plates:
        return {"plates": 0, "records": 0}
    end_date = end_date or max(str(plate.get("latest_date") or "") for plate in plates) or datetime.now().strftime("%Y-%m-%d")
    start_date = _window_start(end_date)

    db = MarketDB(db_path)
    db.init_schema()
    try:
        concept_names, industry_names = load_ths_board_names()
        total_records = 0
        fetched_plates = 0
        for plate in plates:
            records = fetch_plate_index_records(
                plate,
                start_date=start_date,
                end_date=end_date,
                concept_names=concept_names,
                industry_names=industry_names,
            )
            if not records:
                continue
            count = db.import_plate_index_daily(records)
            fetched_plates += 1
            total_records += count
            print(f"  {plate.get('plate_name')}: {count} 条真实板块日线")
    finally:
        db.close()
    return {"plates": fetched_plates, "records": total_records}


def main() -> None:
    parser = argparse.ArgumentParser(description="回补真实板块指数日线数据")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite 数据库路径")
    parser.add_argument("--end-date", help="结束交易日，默认数据库最新涨停日")
    parser.add_argument("--review-days", type=int, default=20, help="从最近多少个交易日里筛核心板块")
    parser.add_argument("--per-day-limit", type=int, default=8, help="核心板块候选规模")
    args = parser.parse_args()

    counts = fetch_plate_index_daily(
        db_path=args.db,
        end_date=args.end_date,
        review_days=args.review_days,
        per_day_limit=args.per_day_limit,
    )
    print(f"完成: 板块 {counts['plates']} 个，日线 {counts['records']} 条")


if __name__ == "__main__":
    main()
