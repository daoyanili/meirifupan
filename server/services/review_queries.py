"""SQL query wrappers for market review data."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).resolve().parent.parent.parent / "data" / "market_review.db")))


def get_connection() -> sqlite3.Connection:
    """Get a new database connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [_row_to_dict(r) for r in rows]


def get_indices(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Get market indices for a given date."""
    rows = conn.execute(
        """
        SELECT index_code, index_name, close_price, change_pct
        FROM market_index_daily
        WHERE trade_date = ?
        """,
        (date,),
    ).fetchall()
    return _rows_to_list(rows)


def get_limit_up_stats(conn: sqlite3.Connection, date: str) -> dict[str, Any]:
    """Get limit-up statistics for a date, including comparison with previous day."""
    row = conn.execute(
        """
        SELECT
            COUNT(DISTINCT stock_code) as total,
            SUM(CASE WHEN up_limit_desc LIKE '%首板%' THEN 1 ELSE 0 END) as first_board,
            SUM(CASE WHEN up_limit_desc NOT LIKE '%首板%' OR up_limit_desc IS NULL THEN 1 ELSE 0 END) as multi_board,
            COALESCE(MAX(up_limit_keep_times), 1) as highest_board
        FROM limit_up_events
        WHERE trade_date = ?
        """,
        (date,),
    ).fetchone()
    current = _row_to_dict(row) if row else {
        "total": 0, "first_board": 0, "multi_board": 0, "highest_board": 1
    }

    # Get previous trading day's total
    prev_row = conn.execute(
        """
        SELECT COUNT(DISTINCT stock_code) as prev_total
        FROM limit_up_events
        WHERE trade_date = (
            SELECT MAX(trade_date) FROM limit_up_events WHERE trade_date < ?
        )
        """,
        (date,),
    ).fetchone()
    current["prev_total"] = prev_row["prev_total"] if prev_row else 0

    return current


def get_board_tiers(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Get board tier breakdown (multi-board stocks grouped by consecutive days)."""
    tiers = conn.execute(
        """
        SELECT
            up_limit_keep_times as level,
            COUNT(*) as count,
            GROUP_CONCAT(stock_name) as stock_names
        FROM limit_up_events
        WHERE trade_date = ? AND up_limit_keep_times >= 2
        GROUP BY up_limit_keep_times
        ORDER BY level DESC
        """,
        (date,),
    ).fetchall()

    result = []
    for tier in tiers:
        level = tier["level"]
        # Get detailed stock info for this tier
        stocks = conn.execute(
            """
            SELECT
                e.stock_code, e.stock_name, e.up_limit_time,
                e.up_limit_type, e.fengdan_money
            FROM limit_up_events e
            WHERE e.trade_date = ? AND e.up_limit_keep_times = ?
            ORDER BY e.fengdan_money DESC
            """,
            (date, level),
        ).fetchall()

        stock_list = []
        for s in stocks:
            stock_dict = _row_to_dict(s)
            # Get plate info for this stock
            plates = conn.execute(
                """
                SELECT p.plate_name
                FROM limit_up_plate_map p
                WHERE p.trade_date = ? AND p.stock_code = ?
                ORDER BY p.plate_score DESC
                LIMIT 3
                """,
                (date, s["stock_code"]),
            ).fetchall()
            stock_dict["plates"] = [p["plate_name"] for p in plates]
            stock_list.append(stock_dict)

        result.append({
            "level": level,
            "count": tier["count"],
            "stock_names": tier["stock_names"],
            "stocks": stock_list,
        })

    return result


def get_hot_plates(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Get top 10 hot plates with limit-up count and historical presence."""
    plates = conn.execute(
        """
        SELECT
            r.plate_code, r.plate_name, r.score, r.rank_no,
            COUNT(DISTINCT m.stock_code) as limit_up_count
        FROM plate_hot_rank r
        LEFT JOIN limit_up_plate_map m
            ON r.trade_date = m.trade_date AND r.plate_code = m.plate_code
        WHERE r.trade_date = ? AND r.source = 'uplimit_hot'
        GROUP BY r.plate_code
        ORDER BY r.rank_no
        LIMIT 10
        """,
        (date,),
    ).fetchall()

    result = []
    for plate in plates:
        p = _row_to_dict(plate)
        plate_code = p["plate_code"]

        # Count how many recent days this plate was in hot rank
        hot_days = conn.execute(
            """
            SELECT COUNT(DISTINCT trade_date) as days
            FROM plate_hot_rank
            WHERE plate_code = ? AND trade_date <= ? AND source = 'uplimit_hot'
            AND trade_date >= date(?, '-30 days')
            """,
            (plate_code, date, date),
        ).fetchone()
        p["days_in_hot"] = hot_days["days"] if hot_days else 0

        # Check if this plate is new (not in hot rank in previous 5 trading days)
        prev_count = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM plate_hot_rank
            WHERE plate_code = ? AND trade_date < ? AND source = 'uplimit_hot'
            AND trade_date >= (
                SELECT trade_date FROM (
                    SELECT DISTINCT trade_date FROM plate_hot_rank
                    WHERE trade_date < ? ORDER BY trade_date DESC LIMIT 5
                ) ORDER BY trade_date ASC LIMIT 1
            )
            """,
            (plate_code, date, date),
        ).fetchone()
        p["is_new"] = (prev_count["cnt"] == 0) if prev_count else True

        result.append(p)

    return result


def get_high_stocks(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Get high stocks: multi-board (>=2) or top fengdan money."""
    stocks = conn.execute(
        """
        SELECT
            e.stock_code, e.stock_name, e.up_limit_keep_times,
            e.up_limit_time, e.up_limit_type, e.fengdan_money,
            e.reason
        FROM limit_up_events e
        WHERE e.trade_date = ?
          AND (e.up_limit_keep_times >= 2 OR e.fengdan_money IS NOT NULL)
        ORDER BY e.up_limit_keep_times DESC, e.fengdan_money DESC
        LIMIT 20
        """,
        (date,),
    ).fetchall()

    result = []
    for s in stocks:
        stock_dict = _row_to_dict(s)
        # Get plate info
        plates = conn.execute(
            """
            SELECT p.plate_name
            FROM limit_up_plate_map p
            WHERE p.trade_date = ? AND p.stock_code = ?
            ORDER BY p.plate_score DESC
            LIMIT 3
            """,
            (date, s["stock_code"]),
        ).fetchall()
        stock_dict["plates"] = [p["plate_name"] for p in plates]
        result.append(stock_dict)

    return result


def get_all_stocks(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Get all limit-up stocks for a date with their primary plate info."""
    stocks = conn.execute(
        """
        SELECT
            e.stock_code, e.stock_name, e.stock_price,
            e.up_limit_time, e.up_limit_desc, e.up_limit_keep_times,
            e.up_limit_type, e.fengdan_money, e.fengdan_rate,
            e.reason, e.amount
        FROM limit_up_events e
        WHERE e.trade_date = ?
        ORDER BY e.up_limit_time ASC
        """,
        (date,),
    ).fetchall()

    result = []
    for s in stocks:
        stock_dict = _row_to_dict(s)
        # Get the highest-ranked plate for this stock as primary plate
        plate_row = conn.execute(
            """
            SELECT p.plate_name, p.plate_code
            FROM limit_up_plate_map p
            LEFT JOIN plate_hot_rank r
                ON p.trade_date = r.trade_date AND p.plate_code = r.plate_code AND r.source = 'uplimit_hot'
            WHERE p.trade_date = ? AND p.stock_code = ?
            ORDER BY COALESCE(r.rank_no, 9999)
            LIMIT 1
            """,
            (date, s["stock_code"]),
        ).fetchone()
        if plate_row:
            stock_dict["primary_plate"] = plate_row["plate_name"]
            stock_dict["primary_plate_code"] = plate_row["plate_code"]
        else:
            stock_dict["primary_plate"] = None
            stock_dict["primary_plate_code"] = None

        # Get all plates
        plates = conn.execute(
            """
            SELECT p.plate_name
            FROM limit_up_plate_map p
            WHERE p.trade_date = ? AND p.stock_code = ?
            ORDER BY p.plate_score DESC
            """,
            (date, s["stock_code"]),
        ).fetchall()
        stock_dict["plates"] = [p["plate_name"] for p in plates]
        result.append(stock_dict)

    return result


def get_dates(conn: sqlite3.Connection) -> list[str]:
    """Get list of available trade dates."""
    rows = conn.execute(
        """
        SELECT DISTINCT trade_date
        FROM limit_up_events
        ORDER BY trade_date DESC
        """
    ).fetchall()
    return [r["trade_date"] for r in rows]


def get_prev_trade_date(conn: sqlite3.Connection, date: str) -> str | None:
    """Get the previous trading date before the given date."""
    row = conn.execute(
        """
        SELECT MAX(trade_date) as prev_date
        FROM limit_up_events
        WHERE trade_date < ?
        """,
        (date,),
    ).fetchone()
    return row["prev_date"] if row else None


def get_recent_dates(conn: sqlite3.Connection, date: str, days: int) -> list[str]:
    """Get up to `days` trading dates ending at `date`."""
    rows = conn.execute(
        """
        SELECT DISTINCT trade_date
        FROM limit_up_events
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
        """,
        (date, days),
    ).fetchall()
    return [r["trade_date"] for r in rows]


def get_seal_quality(conn: sqlite3.Connection, date: str) -> dict[str, Any]:
    """Analyze seal quality distribution for limit-up stocks."""
    row = conn.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN up_limit_type = '一' THEN 1 ELSE 0 END) as one_seal,
            SUM(CASE WHEN up_limit_type NOT LIKE '烂%' AND up_limit_type != '一' THEN 1 ELSE 0 END) as normal_seal,
            SUM(CASE WHEN up_limit_type LIKE '烂%' THEN 1 ELSE 0 END) as broken_seal,
            AVG(CASE WHEN fengdan_rate IS NOT NULL THEN fengdan_rate END) as avg_seal_rate,
            AVG(CASE WHEN fengdan_money IS NOT NULL THEN fengdan_money END) as avg_seal_money,
            SUM(CASE WHEN up_limit_desc LIKE '%首板%' THEN 1 ELSE 0 END) as first_board,
            SUM(CASE WHEN up_limit_desc NOT LIKE '%首板%' OR up_limit_desc IS NULL THEN 1 ELSE 0 END) as multi_board
        FROM limit_up_events
        WHERE trade_date = ?
        """,
        (date,),
    ).fetchone()

    if not row:
        return {"total": 0, "one_seal": 0, "normal_seal": 0, "broken_seal": 0,
                "avg_seal_rate": 0, "avg_seal_money": 0, "first_board": 0, "multi_board": 0}

    result = _row_to_dict(row)

    # Compute derived metrics
    total = result["total"]
    result["broken_rate"] = round(result["broken_seal"] / total * 100, 1) if total > 0 else 0
    result["one_seal_rate"] = round(result["one_seal"] / total * 100, 1) if total > 0 else 0
    result["first_board_rate"] = round(result["first_board"] / total * 100, 1) if total > 0 else 0

    # Get previous day for comparison
    prev_date = get_prev_trade_date(conn, date)
    if prev_date:
        prev_row = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN up_limit_type LIKE '烂%' THEN 1 ELSE 0 END) as broken_seal,
                AVG(CASE WHEN fengdan_rate IS NOT NULL THEN fengdan_rate END) as avg_seal_rate
            FROM limit_up_events WHERE trade_date = ?
            """,
            (prev_date,),
        ).fetchone()
        if prev_row:
            prev = _row_to_dict(prev_row)
            result["prev_total"] = prev["total"]
            result["prev_broken_rate"] = round(prev["broken_seal"] / prev["total"] * 100, 1) if prev["total"] > 0 else 0
            result["prev_avg_seal_rate"] = prev["avg_seal_rate"] or 0
    else:
        result["prev_total"] = 0
        result["prev_broken_rate"] = 0
        result["prev_avg_seal_rate"] = 0

    return result


def get_board_advancement(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Analyze board advancement: how many N-board stocks from prev day advanced to N+1."""
    prev_date = get_prev_trade_date(conn, date)
    if not prev_date:
        return []

    # Get prev day's stocks by board count
    prev_stocks = conn.execute(
        """
        SELECT stock_code, stock_name, up_limit_keep_times
        FROM limit_up_events
        WHERE trade_date = ?
        """,
        (prev_date,),
    ).fetchall()

    # Get current day's stocks
    cur_stocks = conn.execute(
        """
        SELECT stock_code, up_limit_keep_times
        FROM limit_up_events
        WHERE trade_date = ?
        """,
        (date,),
    ).fetchall()

    cur_map = {s["stock_code"]: s["up_limit_keep_times"] for s in cur_stocks}

    # Group prev stocks by board level
    prev_by_level: dict[int, list] = {}
    for s in prev_stocks:
        level = s["up_limit_keep_times"]
        if level not in prev_by_level:
            prev_by_level[level] = []
        prev_by_level[level].append(s)

    result = []
    for level in sorted(prev_by_level.keys(), reverse=True):
        stocks = prev_by_level[level]
        total = len(stocks)
        advanced = 0
        maintained = 0
        failed = 0
        failed_names = []

        for s in stocks:
            cur_level = cur_map.get(s["stock_code"])
            if cur_level is not None:
                if cur_level > level:
                    advanced += 1
                else:
                    maintained += 1
            else:
                failed += 1
                failed_names.append(s["stock_name"])

        result.append({
            "level": level,
            "total": total,
            "advanced": advanced,
            "maintained": maintained,
            "failed": failed,
            "advancement_rate": round((advanced / total) * 100, 1) if total > 0 else 0,
            "fail_rate": round((failed / total) * 100, 1) if total > 0 else 0,
            "failed_names": failed_names[:5],
        })

    return result


def get_capital_flow(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Get top plates by net capital flow from plate_daily."""
    rows = conn.execute(
        """
        SELECT
            plate_code, plate_name, raw_payload
        FROM plate_daily
        WHERE trade_date = ?
        ORDER BY plate_code
        """,
        (date,),
    ).fetchall()

    result = []
    import json
    for row in rows:
        try:
            payload = json.loads(row["raw_payload"])
        except (json.JSONDecodeError, TypeError):
            continue

        money_leader = payload.get("money_leader", 0)
        result.append({
            "plate_code": row["plate_code"],
            "plate_name": row["plate_name"],
            "net_flow": money_leader,
            "buy": payload.get("money_leader_buy", 0),
            "sell": payload.get("money_leader_sell", 0),
            "rate": payload.get("rate", 0),
            "trade_money": payload.get("trade_money", 0),
            "volume_ration": payload.get("volume_ration", 0),
        })

    # Sort by absolute net flow descending
    result.sort(key=lambda x: abs(x["net_flow"]), reverse=True)
    return result[:20]


def get_hot_stocks_derived(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Derive hot stocks from fengdan_money and cross-plate presence."""
    # Top stocks by fengdan_money
    stocks = conn.execute(
        """
        SELECT
            e.stock_code, e.stock_name, e.up_limit_keep_times,
            e.up_limit_time, e.up_limit_type, e.fengdan_money,
            e.fengdan_rate, e.reason, e.amount
        FROM limit_up_events e
        WHERE e.trade_date = ? AND e.fengdan_money IS NOT NULL
        ORDER BY e.fengdan_money DESC
        LIMIT 20
        """,
        (date,),
    ).fetchall()

    result = []
    for s in stocks:
        d = _row_to_dict(s)
        # Get plates
        plates = conn.execute(
            """
            SELECT p.plate_name
            FROM limit_up_plate_map p
            WHERE p.trade_date = ? AND p.stock_code = ?
            ORDER BY p.plate_score DESC
            """,
            (date, s["stock_code"]),
        ).fetchall()
        d["plates"] = [p["plate_name"] for p in plates]
        d["plate_count"] = len(plates)
        result.append(d)

    return result


def get_hot_stocks_rank(conn: sqlite3.Connection, date: str, limit: int = 30) -> list[dict[str, Any]]:
    """Get hot stock rankings from hot_stocks table."""
    rows = conn.execute(
        """
        SELECT rank_no, stock_code, stock_name, latest_price, change_pct, change_amount
        FROM hot_stocks
        WHERE trade_date = ?
        ORDER BY rank_no
        LIMIT ?
        """,
        (date, limit),
    ).fetchall()
    return _rows_to_list(rows)


def get_hot_boards_rank(conn: sqlite3.Connection, date: str, board_type: str = "concept", limit: int = 20) -> list[dict[str, Any]]:
    """Get hot board rankings from hot_boards table."""
    rows = conn.execute(
        """
        SELECT rank_no, board_code, board_name, latest_price, change_pct, change_amount,
               total_market_cap, turnover_rate, up_count, down_count,
               leading_stock, leading_stock_change
        FROM hot_boards
        WHERE trade_date = ? AND board_type = ?
        ORDER BY rank_no
        LIMIT ?
        """,
        (date, board_type, limit),
    ).fetchall()
    return _rows_to_list(rows)


def get_hot_available_dates(conn: sqlite3.Connection) -> list[str]:
    """Get dates that have hot stock/board data."""
    rows = conn.execute(
        """
        SELECT DISTINCT trade_date FROM hot_stocks
        UNION
        SELECT DISTINCT trade_date FROM hot_boards
        ORDER BY trade_date DESC
        """
    ).fetchall()
    return [r["trade_date"] for r in rows]
