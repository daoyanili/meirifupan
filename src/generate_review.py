"""Generate structured daily review reports from the local market database."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MarketDB


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports"


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [_row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


def _row(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    return _row_to_dict(row) if row else None


def _fmt_money(value: float | int | None) -> str:
    if value is None:
        return "-"
    if abs(value) >= 100000000:
        return f"{value / 100000000:.1f}亿"
    if abs(value) >= 10000:
        return f"{value / 10000:.0f}万"
    return f"{value:.0f}"


def _safe_int(value: Any, default: int = 0) -> int:
    return int(value) if value is not None else default


def _safe_float(value: Any, default: float = 0.0) -> float:
    return float(value) if value is not None else default


def _fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "-"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:.1f}%"


def _brief_text(value: Any, max_len: int = 120) -> str:
    text = str(value or "").replace("\r", "\n").strip()
    if not text:
        return ""
    first = next((part.strip() for part in text.split("\n") if part.strip()), "")
    if len(first) <= max_len:
        return first
    return first[:max_len].rstrip() + "..."


def get_default_date(db_path: str | Path = DEFAULT_DB_PATH) -> str:
    conn = _connect(db_path)
    try:
        row = conn.execute("select max(trade_date) as trade_date from limit_up_events").fetchone()
        if not row or not row["trade_date"]:
            raise RuntimeError("数据库里还没有涨停数据")
        return row["trade_date"]
    finally:
        conn.close()


def _hot_stock_signal(stock: dict[str, Any]) -> str:
    if stock.get("is_limit_up"):
        return "人气和涨停重合，短线资金已经给出态度。"
    change_pct = stock.get("change_pct")
    if change_pct is None:
        return "人气靠前但缺少涨跌幅，先看成交能不能延续。"
    if change_pct >= 5:
        return "没封板也能大涨，是趋势资金在主动进攻。"
    if change_pct <= -5:
        return "人气还在但股价大跌，这是高位分歧的风向标。"
    if change_pct > 0:
        return "没涨停但能红，说明还有资金愿意做承接。"
    return "人气没散但股价回落，明天先看是否继续失血。"


def build_hot_stocks(conn: sqlite3.Connection, trade_date: str, limit: int = 20) -> list[dict[str, Any]]:
    hot_stocks = _rows(
        conn,
        """
        select
            h.rank_no, h.stock_code, h.stock_name, h.latest_price,
            h.change_pct, h.change_amount,
            case when e.stock_code is null then 0 else 1 end as is_limit_up,
            e.up_limit_keep_times,
            e.fengdan_money,
            (
                select p.plate_name
                from limit_up_plate_map p
                where p.trade_date = h.trade_date and p.stock_code = h.stock_code
                order by coalesce(p.plate_score, 0) desc
                limit 1
            ) as primary_plate
        from hot_stocks h
        left join limit_up_events e
            on h.trade_date = e.trade_date and h.stock_code = e.stock_code
        where h.trade_date = ?
        order by h.rank_no asc
        limit ?
        """,
        (trade_date, limit),
    )
    for stock in hot_stocks:
        stock["is_limit_up"] = bool(stock.get("is_limit_up"))
        stock["signal"] = _hot_stock_signal(stock)
    return hot_stocks


def build_hot_stock_summary(hot_stocks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(hot_stocks)
    if not total:
        return {
            "total": 0,
            "limit_up_count": 0,
            "non_limit_up_count": 0,
            "rising_count": 0,
            "falling_count": 0,
            "text": "这一天没有可用的人气榜数据，报告先按涨停、板块和资金数据判断。",
        }

    limit_up_count = sum(1 for stock in hot_stocks if stock.get("is_limit_up"))
    non_limit_up_count = total - limit_up_count
    rising = [stock for stock in hot_stocks if stock.get("change_pct") is not None and stock["change_pct"] > 0]
    falling = [stock for stock in hot_stocks if stock.get("change_pct") is not None and stock["change_pct"] < 0]
    top_names = "、".join(stock["stock_name"] for stock in hot_stocks[:3] if stock.get("stock_name"))
    lead = f"今天人气榜先看 {top_names}" if top_names else "今天人气榜没有清晰前排"
    top_non_limit = [stock for stock in hot_stocks[:5] if not stock.get("is_limit_up")]
    heavy_falling = [stock for stock in hot_stocks if stock.get("change_pct") is not None and stock["change_pct"] <= -5]
    strong_rising = [stock for stock in hot_stocks if stock.get("change_pct") is not None and stock["change_pct"] >= 5]
    falling_names = "、".join(stock["stock_name"] for stock in heavy_falling[:3] if stock.get("stock_name"))
    rising_names = "、".join(stock["stock_name"] for stock in strong_rising[:3] if stock.get("stock_name"))

    if len(top_non_limit) >= 3 or non_limit_up_count > limit_up_count:
        structure = "这不是涨停接力行情，资金主要挤在高人气趋势股里。"
    elif limit_up_count:
        structure = "人气榜里有涨停股，短线情绪和市场关注点有重合。"
    else:
        structure = "人气榜和涨停池重合度不高，单看涨停会漏掉真正的前排。"

    if heavy_falling:
        action = f"{falling_names} 这类高人气票跌得重，明天先看它们能不能止跌；止不住，题材热度容易继续降温。"
    elif strong_rising:
        action = f"{rising_names} 这种没封板也能走强的票更像主动资金，明天看回踩时有没有承接。"
    else:
        action = "明天重点看前排人气股是继续放量上攻，还是冲高回落。"

    return {
        "total": total,
        "limit_up_count": limit_up_count,
        "non_limit_up_count": non_limit_up_count,
        "rising_count": len(rising),
        "falling_count": len(falling),
        "text": (
            f"{lead}。前{total}名里非涨停 {non_limit_up_count} 只、涨停 {limit_up_count} 只，"
            f"上涨 {len(rising)} 只、下跌 {len(falling)} 只。{structure}{action}"
        ),
    }


def build_watch_stocks(
    hot_stocks: list[dict[str, Any]],
    core_stocks: list[dict[str, Any]],
    lhb_buy: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    watch: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(stock: dict[str, Any], category: str, reason: str) -> None:
        stock_code = str(stock.get("stock_code") or "")
        if not stock_code or stock_code in seen:
            return
        seen.add(stock_code)
        watch.append(
            {
                "stock_code": stock_code,
                "stock_name": stock.get("stock_name"),
                "category": category,
                "reason": reason,
                "change_pct": stock.get("change_pct"),
                "rank_no": stock.get("rank_no"),
                "primary_plate": stock.get("primary_plate"),
            }
        )

    hot_core_count = 0
    for stock in hot_stocks:
        if hot_core_count >= 6:
            break
        if not stock.get("is_limit_up"):
            change_text = _fmt_pct(stock.get("change_pct"))
            add(stock, "人气核心", f"人气#{stock.get('rank_no')}，非涨停，{change_text}，它是今天趋势股强弱的风向标。")
            hot_core_count += 1

    for stock in core_stocks[:4]:
        add(
            stock,
            "涨停核心",
            f"{stock.get('up_limit_keep_times') or 1}板，封单 {_fmt_money(stock.get('fengdan_money'))}。",
        )

    for stock in lhb_buy[:3]:
        add(stock, "资金核心", f"龙虎榜净买 {_fmt_money(stock.get('net_buy_amount'))}。")

    return watch[:10]


def _recent_trade_dates(conn: sqlite3.Connection, trade_date: str, days: int = 5) -> list[str]:
    rows = conn.execute(
        """
        select distinct trade_date
        from limit_up_events
        where trade_date <= ?
        order by trade_date desc
        limit ?
        """,
        (trade_date, days),
    ).fetchall()
    return [row["trade_date"] for row in reversed(rows)]


def _plate_activity_map(
    conn: sqlite3.Connection,
    plate_code: str,
    dates: list[str],
) -> dict[str, dict[str, Any]]:
    if not dates:
        return {}
    placeholders = ",".join(["?"] * len(dates))
    rows = conn.execute(
        f"""
        select
            p.trade_date,
            count(distinct p.stock_code) as limit_up_count,
            coalesce(sum(e.fengdan_money), 0) as seal_amount
        from limit_up_plate_map p
        left join limit_up_events e
            on p.trade_date = e.trade_date and p.stock_code = e.stock_code
        where p.plate_code = ? and p.trade_date in ({placeholders})
        group by p.trade_date
        """,
        (plate_code, *dates),
    ).fetchall()
    data = {row["trade_date"]: _row_to_dict(row) for row in rows}
    return {
        date: {
            "trade_date": date,
            "limit_up_count": _safe_int((data.get(date) or {}).get("limit_up_count")),
            "seal_amount": (data.get(date) or {}).get("seal_amount") or 0,
        }
        for date in dates
    }


def _build_plate_core_stocks(
    conn: sqlite3.Connection,
    plate_code: str,
    trade_date: str,
    dates: list[str],
    limit: int = 6,
) -> list[dict[str, Any]]:
    if not dates:
        return []
    placeholders = ",".join(["?"] * len(dates))
    rows = _rows(
        conn,
        f"""
        select
            p.stock_code,
            coalesce(max(e.stock_name), max(s.stock_name)) as stock_name,
            count(distinct p.trade_date) as active_days,
            max(case when p.trade_date = ? then 1 else 0 end) as is_today_limit_up,
            max(coalesce(e.up_limit_keep_times, 1)) as highest_board,
            coalesce(sum(e.fengdan_money), 0) as total_seal_amount,
            max(h.rank_no) as hot_rank,
            max(h.change_pct) as hot_change_pct,
            group_concat(distinct coalesce(nullif(p.stock_reason, ''), nullif(e.reason, ''))) as reasons
        from limit_up_plate_map p
        left join limit_up_events e
            on p.trade_date = e.trade_date and p.stock_code = e.stock_code
        left join stocks s
            on p.stock_code = s.stock_code
        left join hot_stocks h
            on h.trade_date = ? and h.stock_code = p.stock_code
        where p.plate_code = ? and p.trade_date in ({placeholders})
        group by p.stock_code
        order by active_days desc,
                 is_today_limit_up desc,
                 coalesce(hot_rank, 999999) asc,
                 highest_board desc,
                 total_seal_amount desc
        limit ?
        """,
        (trade_date, trade_date, plate_code, *dates, limit),
    )
    result = []
    for row in rows:
        is_today = bool(row.get("is_today_limit_up"))
        reason = "板块核心"
        if row.get("hot_rank"):
            reason += f"，人气#{row['hot_rank']}"
        if row.get("active_days"):
            reason += f"，近{len(dates)}日出现 {row['active_days']} 天"
        if is_today:
            reason += "，今天仍在涨停池"
        result.append(
            {
                "stock_code": row.get("stock_code"),
                "stock_name": row.get("stock_name"),
                "active_days": _safe_int(row.get("active_days")),
                "is_today_limit_up": is_today,
                "highest_board": _safe_int(row.get("highest_board"), 1),
                "hot_rank": row.get("hot_rank"),
                "hot_change_pct": row.get("hot_change_pct"),
                "total_seal_amount": row.get("total_seal_amount"),
                "reason": reason + "。",
                "event_reason": _brief_text(row.get("reasons"), 80),
            }
        )
    return result


def _plate_review_text(
    plate_name: str,
    dates: list[str],
    activity: list[dict[str, Any]],
    core_stocks: list[dict[str, Any]],
    index_summary: dict[str, Any] | None = None,
) -> tuple[str, str]:
    counts = [_safe_int(item.get("limit_up_count")) for item in activity]
    today = counts[-1] if counts else 0
    yesterday = counts[-2] if len(counts) >= 2 else 0
    active_days = sum(1 for count in counts if count > 0)
    max_count = max(counts) if counts else 0
    if len(counts) >= 2 and today > yesterday:
        trend = "升温"
    elif len(counts) >= 2 and today < yesterday:
        trend = "降温"
    elif active_days >= max(3, len(dates) - 1):
        trend = "持续活跃"
    else:
        trend = "观察"

    leader_text = "、".join(stock["stock_name"] for stock in core_stocks[:3] if stock.get("stock_name")) or "-"
    index_text = ""
    if index_summary:
        today_change = index_summary.get("today_change_pct")
        window_change = index_summary.get("window_change_pct")
        index_text = (
            f"真实涨跌：今日 {_fmt_pct(today_change)}，"
            f"近{index_summary.get('window_days') or len(dates)}日 {_fmt_pct(window_change)}。"
        )
    delta = today - yesterday
    if len(counts) >= 2:
        if delta > 0:
            heat_text = f"今天涨停从 {yesterday} 只增到 {today} 只"
        elif delta < 0:
            heat_text = f"今天涨停从 {yesterday} 只降到 {today} 只"
        else:
            heat_text = f"今天涨停维持在 {today} 只"
    else:
        heat_text = f"今天涨停 {today} 只"
    activity_text = f"近{len(dates)}日有 {active_days} 天出现在涨停池，期间单日最高 {max_count} 只"
    if trend == "升温":
        action = "明天看前排能不能继续顶住，后排补涨才有意义。"
    elif trend == "降温":
        action = "明天先看核心股能不能止跌或弱转强，后排不要急着追。"
    elif trend == "持续活跃":
        action = "明天重点看核心股是否继续扩散，断板后的承接也很关键。"
    else:
        action = "明天只先当观察方向，看有没有新的前排确认。"

    text = (
        f"{activity_text}，{heat_text}。"
        f"{index_text}核心看 {leader_text}。{action}"
    )
    return trend, text


def _plate_index_summary(
    conn: sqlite3.Connection,
    plate_code: str,
    trade_date: str,
    dates: list[str],
) -> dict[str, Any] | None:
    if not dates:
        return None
    rows = _rows(
        conn,
        """
        select plate_code, plate_name, trade_date, source, board_type,
               open_price, high_price, low_price, close_price, change_pct,
               volume, amount
        from plate_index_daily
        where plate_code = ? and trade_date <= ?
        order by trade_date desc
        limit ?
        """,
        (plate_code, trade_date, len(dates)),
    )
    if not rows:
        return None
    rows = list(reversed(rows))
    first_close = rows[0].get("close_price")
    last_close = rows[-1].get("close_price")
    window_change = None
    if first_close and last_close is not None:
        window_change = round((last_close - first_close) / first_close * 100, 2)
    return {
        "source": rows[-1].get("source"),
        "board_type": rows[-1].get("board_type"),
        "window_days": len(rows),
        "start_trade_date": rows[0].get("trade_date"),
        "end_trade_date": rows[-1].get("trade_date"),
        "start_close": first_close,
        "end_close": last_close,
        "today_change_pct": rows[-1].get("change_pct"),
        "window_change_pct": window_change,
        "amount": rows[-1].get("amount"),
        "series": rows,
    }


def build_plate_reviews(
    conn: sqlite3.Connection,
    trade_date: str,
    strongest_plates: list[dict[str, Any]],
    window: int = 5,
) -> list[dict[str, Any]]:
    dates = _recent_trade_dates(conn, trade_date, window)
    reviews: list[dict[str, Any]] = []
    seen_core_sets: list[set[str]] = []
    for plate in strongest_plates:
        plate_code = str(plate.get("plate_code") or "")
        if not plate_code:
            continue
        activity_map = _plate_activity_map(conn, plate_code, dates)
        activity = [activity_map[date] for date in dates]
        core_stocks = _build_plate_core_stocks(conn, plate_code, trade_date, dates)
        core_set = {str(stock.get("stock_code") or "") for stock in core_stocks[:4] if stock.get("stock_code")}
        if core_set and any(len(core_set & existing) >= min(3, len(core_set), len(existing)) for existing in seen_core_sets):
            continue
        seen_core_sets.append(core_set)
        index_summary = _plate_index_summary(conn, plate_code, trade_date, dates)
        trend, text = _plate_review_text(plate.get("plate_name") or plate_code, dates, activity, core_stocks, index_summary)
        reviews.append(
            {
                "plate_code": plate_code,
                "plate_name": plate.get("plate_name"),
                "data_scope": "limit_up_activity",
                "window_days": len(dates),
                "active_days": sum(1 for item in activity if _safe_int(item.get("limit_up_count")) > 0),
                "today_limit_up_count": activity[-1]["limit_up_count"] if activity else 0,
                "trend": trend,
                "review_text": text,
                "index_summary": index_summary,
                "activity": activity,
                "core_stocks": core_stocks,
            }
        )
    return reviews


def build_review_payload(trade_date: str, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    conn = _connect(db_path)
    try:
        stats = _row(
            conn,
            """
            select
                (select count(distinct stock_code) from limit_up_events where trade_date = ?) as limit_up_stock_count,
                (select count(distinct plate_code) from limit_up_plate_map where trade_date = ?) as limit_up_plate_count,
                sum(case when coalesce(up_limit_desc, '') like '%首板%' then 1 else 0 end) as first_board_count,
                sum(case when coalesce(up_limit_desc, '') not like '%首板%' then 1 else 0 end) as multi_board_count,
                coalesce(max(up_limit_keep_times), 1) as highest_board
            from limit_up_events
            where trade_date = ?
            """,
            (trade_date, trade_date, trade_date),
        ) or {}
        if _safe_int(stats.get("limit_up_stock_count")) == 0:
            raise RuntimeError(f"{trade_date} 没有涨停数据，无法生成复盘")

        prev = _row(
            conn,
            """
            select trade_date, count(distinct stock_code) as limit_up_stock_count
            from limit_up_events
            where trade_date = (select max(trade_date) from limit_up_events where trade_date < ?)
            """,
            (trade_date,),
        ) or {"trade_date": None, "limit_up_stock_count": 0}

        breadth = _row(
            conn,
            """
            select total_count, up_count, down_count, flat_count, limit_up_count, limit_down_count, amount
            from market_breadth_daily
            where trade_date = ?
            """,
            (trade_date,),
        ) or {
            "total_count": 0,
            "up_count": 0,
            "down_count": 0,
            "flat_count": 0,
            "limit_up_count": stats.get("limit_up_stock_count"),
            "limit_down_count": None,
            "amount": None,
        }
        limit_down_total = _row(
            conn,
            "select count(*) as total from limit_down_events where trade_date = ?",
            (trade_date,),
        )["total"]
        broken_total = _row(
            conn,
            "select count(*) as total from broken_limit_up_events where trade_date = ?",
            (trade_date,),
        )["total"]
        if not breadth.get("limit_down_count") and limit_down_total:
            breadth["limit_down_count"] = limit_down_total
        up_rate = (
            round((breadth.get("up_count") or 0) / breadth["total_count"] * 100, 1)
            if breadth.get("total_count")
            else None
        )

        strongest_plates = _rows(
            conn,
            """
            select
                p.plate_code,
                p.plate_name,
                count(distinct p.stock_code) as limit_up_count,
                max(coalesce(r.score, p.plate_score, 0)) as score,
                group_concat(distinct e.stock_name) as stock_names
            from limit_up_plate_map p
            left join limit_up_events e
                on p.trade_date = e.trade_date and p.stock_code = e.stock_code
            left join plate_hot_rank r
                on p.trade_date = r.trade_date and p.plate_code = r.plate_code and r.source = 'uplimit_hot'
            where p.trade_date = ?
            group by p.plate_code, p.plate_name
            order by limit_up_count desc, score desc
            limit 6
            """,
            (trade_date,),
        )
        for plate in strongest_plates:
            count = _safe_int(plate.get("limit_up_count"))
            if count >= 8:
                stage = "主线"
            elif count >= 4:
                stage = "活跃"
            else:
                stage = "观察"
            plate["stage"] = stage
            plate["stocks"] = (plate.pop("stock_names") or "").split(",")[:8]

        core_stocks = _rows(
            conn,
            """
            select
                e.stock_code, e.stock_name, e.up_limit_keep_times,
                e.up_limit_time, e.fengdan_money, e.reason,
                (
                    select p.plate_name
                    from limit_up_plate_map p
                    where p.trade_date = e.trade_date and p.stock_code = e.stock_code
                    order by coalesce(p.plate_score, 0) desc
                    limit 1
                ) as primary_plate
            from limit_up_events e
            where e.trade_date = ?
            order by coalesce(e.up_limit_keep_times, 1) desc,
                     coalesce(e.fengdan_money, 0) desc,
                     e.up_limit_time asc
            limit 12
            """,
            (trade_date,),
        )

        indices = _rows(
            conn,
            """
            select index_code, index_name, close_price, change_pct
            from market_index_daily
            where trade_date = ?
            order by index_code
            """,
            (trade_date,),
        )

        lhb_buy = _rows(
            conn,
            """
            select stock_code, stock_name, reason, net_buy_amount
            from lhb_daily
            where trade_date = ? and coalesce(net_buy_amount, 0) > 0
            order by net_buy_amount desc
            limit 5
            """,
            (trade_date,),
        )
        hot_stocks = build_hot_stocks(conn, trade_date)
        hot_stock_summary = build_hot_stock_summary(hot_stocks)
        watch_stocks = build_watch_stocks(hot_stocks, core_stocks, lhb_buy)
        plate_reviews = build_plate_reviews(conn, trade_date, strongest_plates)

        risk_flags = build_risk_flags(
            stats=stats,
            prev=prev,
            breadth=breadth,
            up_rate=up_rate,
            limit_down_total=limit_down_total,
            broken_total=broken_total,
        )
        opportunities = build_opportunities(strongest_plates, core_stocks, lhb_buy, hot_stocks)
        next_plan = build_next_plan(stats, strongest_plates, risk_flags)
        summary = build_summary(
            trade_date=trade_date,
            stats=stats,
            prev=prev,
            strongest_plates=strongest_plates,
            breadth=breadth,
            up_rate=up_rate,
            limit_down_total=limit_down_total,
            broken_total=broken_total,
            hot_stocks=hot_stocks,
            hot_stock_summary=hot_stock_summary,
        )

        return {
            "trade_date": trade_date,
            "limit_up_stock_count": _safe_int(stats.get("limit_up_stock_count")),
            "limit_up_plate_count": _safe_int(stats.get("limit_up_plate_count")),
            "first_board_count": _safe_int(stats.get("first_board_count")),
            "multi_board_count": _safe_int(stats.get("multi_board_count")),
            "highest_board": _safe_int(stats.get("highest_board"), 1),
            "prev_trade_date": prev.get("trade_date"),
            "prev_limit_up_stock_count": _safe_int(prev.get("limit_up_stock_count")),
            "breadth": {
                **breadth,
                "up_rate": up_rate,
                "limit_down_total": limit_down_total,
                "broken_limit_up_total": broken_total,
            },
            "indices": indices,
            "strongest_plates": strongest_plates,
            "plate_reviews": plate_reviews,
            "core_stocks": core_stocks,
            "hot_stock_summary": hot_stock_summary,
            "hot_stocks": hot_stocks,
            "watch_stocks": watch_stocks,
            "lhb_net_buy": lhb_buy,
            "risk_flags": risk_flags,
            "opportunities": opportunities,
            "next_plan": next_plan,
            "summary": summary,
            "markdown_path": None,
        }
    finally:
        conn.close()


def build_summary(
    trade_date: str,
    stats: dict[str, Any],
    prev: dict[str, Any],
    strongest_plates: list[dict[str, Any]],
    breadth: dict[str, Any],
    up_rate: float | None,
    limit_down_total: int,
    broken_total: int,
    hot_stocks: list[dict[str, Any]] | None = None,
    hot_stock_summary: dict[str, Any] | None = None,
) -> str:
    total = _safe_int(stats.get("limit_up_stock_count"))
    prev_total = _safe_int(prev.get("limit_up_stock_count"))
    delta = total - prev_total if prev_total else 0
    strongest = strongest_plates[0]["plate_name"] if strongest_plates else "暂无明显主线"
    direction = "增加" if delta > 0 else "减少" if delta < 0 else "持平"
    breadth_text = f"，红盘率 {up_rate:.1f}%" if up_rate is not None else ""
    hot_text = ""
    if hot_stocks:
        hot_names = "、".join(stock["stock_name"] for stock in hot_stocks[:3] if stock.get("stock_name"))
        non_limit_up_count = _safe_int((hot_stock_summary or {}).get("non_limit_up_count"))
        limit_up_count = _safe_int((hot_stock_summary or {}).get("limit_up_count"))
        if hot_names:
            if non_limit_up_count > limit_up_count:
                hot_text = f" 人气前排是 {hot_names}，但基本没走涨停接力，更像趋势股分歧盘。"
            else:
                hot_text = f" 人气前排是 {hot_names}，短线情绪和人气方向有重合。"
    return (
        f"{trade_date} 涨停 {total} 只，较前一交易日{direction} {abs(delta)} 只，"
        f"最高板 {stats.get('highest_board') or 1} 板，主线集中在 {strongest}"
        f"{breadth_text}。跌停 {breadth.get('limit_down_count') or limit_down_total} 只，"
        f"炸板 {broken_total} 只，明天重点看主线延续和高位分歧。{hot_text}"
    )


def build_risk_flags(
    stats: dict[str, Any],
    prev: dict[str, Any],
    breadth: dict[str, Any],
    up_rate: float | None,
    limit_down_total: int,
    broken_total: int,
) -> list[str]:
    risks = []
    total = _safe_int(stats.get("limit_up_stock_count"))
    prev_total = _safe_int(prev.get("limit_up_stock_count"))
    if prev_total and total < prev_total * 0.7:
        risks.append(f"涨停数较前一交易日明显收缩：{prev_total} -> {total}。")
    if broken_total >= max(20, total * 0.45):
        risks.append(f"炸板数量偏高：{broken_total} 只，说明封板稳定性一般。")
    limit_down_count = _safe_int(breadth.get("limit_down_count")) or limit_down_total
    if limit_down_count >= 20:
        risks.append(f"跌停数量偏多：{limit_down_count} 只，亏钱效应需要警惕。")
    if up_rate is not None and up_rate < 45:
        risks.append(f"红盘率偏低：{up_rate:.1f}%，市场宽度不足。")
    if _safe_int(stats.get("highest_board"), 1) <= 3:
        risks.append("连板高度不高，高标带动性还不够强。")
    if not risks:
        risks.append("暂未看到明显系统性风险，但高位股仍要观察分歧承接。")
    return risks


def build_opportunities(
    strongest_plates: list[dict[str, Any]],
    core_stocks: list[dict[str, Any]],
    lhb_buy: list[dict[str, Any]],
    hot_stocks: list[dict[str, Any]] | None = None,
) -> list[str]:
    opportunities = []
    hot_stocks = hot_stocks or []
    hot_non_limit = [stock for stock in hot_stocks if not stock.get("is_limit_up")]
    hot_rising = [stock for stock in hot_non_limit if _safe_float(stock.get("change_pct")) > 0]
    if hot_non_limit:
        names = "、".join(
            f"{stock['stock_name']}({_fmt_pct(stock.get('change_pct'))})"
            for stock in (hot_rising or hot_non_limit)[:3]
            if stock.get("stock_name")
        )
        if names:
            opportunities.append(f"非涨停人气股：{names}，明天先看承接，别把它们当普通杂毛处理。")
    for plate in strongest_plates[:3]:
        stocks = "、".join(plate.get("stocks") or [])
        suffix = f"，代表股：{stocks}" if stocks else ""
        opportunities.append(
            f"{plate['plate_name']}：{plate.get('limit_up_count', 0)} 只涨停，状态为{plate.get('stage', '观察')}{suffix}。"
        )
    if lhb_buy:
        top = lhb_buy[0]
        opportunities.append(f"龙虎榜净买入靠前：{top['stock_name']}，净买 {_fmt_money(top['net_buy_amount'])}。")
    if not opportunities and core_stocks:
        top = core_stocks[0]
        opportunities.append(f"核心观察股：{top['stock_name']}，{top.get('up_limit_keep_times') or 1} 板。")
    return opportunities


def build_next_plan(
    stats: dict[str, Any],
    strongest_plates: list[dict[str, Any]],
    risk_flags: list[str],
) -> list[str]:
    plan = []
    if strongest_plates:
        plan.append(f"优先观察 {strongest_plates[0]['plate_name']} 是否继续扩散，确认主线持续性。")
    if _safe_int(stats.get("highest_board"), 1) >= 5:
        plan.append("高标进入情绪锚定区，明天先看最高板反馈，再决定进攻强度。")
    else:
        plan.append("高度还没完全打开，明天更适合看首板和二板的强度确认。")
    if len(risk_flags) >= 2 and "暂未看到明显系统性风险" not in risk_flags[0]:
        plan.append("若早盘继续出现跌停或炸板扩大，降低追高，优先保留现金。")
    else:
        plan.append("若主线前排继续强势，低位补涨和换手核心可以作为观察重点。")
    return plan


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "---",
        f"date: {review['trade_date']}",
        "tags: [复盘, A股, 短线]",
        "---",
        "",
        f"# A股复盘 {review['trade_date']}",
        "",
        "## 一句话结论",
        "",
        review["summary"],
        "",
        "## 盘面数据",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 涨停 | {review['limit_up_stock_count']} |",
        f"| 首板 / 连板 | {review['first_board_count']} / {review['multi_board_count']} |",
        f"| 最高板 | {review['highest_board']} |",
        f"| 跌停 | {review['breadth'].get('limit_down_count') or review['breadth'].get('limit_down_total')} |",
        f"| 炸板 | {review['breadth'].get('broken_limit_up_total')} |",
        f"| 红盘率 | {review['breadth'].get('up_rate') if review['breadth'].get('up_rate') is not None else '-'}% |",
        f"| 成交额 | {_fmt_money(review['breadth'].get('amount'))} |",
        "",
        "## 主线板块",
        "",
    ]
    for plate in review["strongest_plates"]:
        stocks = "、".join(plate.get("stocks") or [])
        lines.append(f"- **{plate['plate_name']}**：{plate.get('limit_up_count', 0)} 只涨停，{plate.get('stage', '观察')}。{stocks}")

    if review.get("plate_reviews"):
        lines.extend(["", "## 核心板块复盘", ""])
        for plate in review["plate_reviews"][:6]:
            lines.append(f"- **{plate.get('plate_name')}**（{plate.get('trend')}）：{plate.get('review_text')}")
            stocks = "、".join(
                f"{stock.get('stock_name')}({stock.get('reason')})"
                for stock in (plate.get("core_stocks") or [])[:3]
                if stock.get("stock_name")
            )
            if stocks:
                lines.append(f"  - 核心股：{stocks}")

    if review.get("hot_stocks"):
        lines.extend(["", "## 人气核心", ""])
        summary_text = (review.get("hot_stock_summary") or {}).get("text")
        if summary_text:
            lines.append(summary_text)
            lines.append("")
        for stock in review["hot_stocks"][:10]:
            limit_text = "涨停" if stock.get("is_limit_up") else "非涨停"
            lines.append(
                f"- #{stock.get('rank_no')} {stock['stock_name']}（{stock['stock_code']}）："
                f"{limit_text}，涨跌幅 {_fmt_pct(stock.get('change_pct'))}，{stock.get('signal') or ''}"
            )

    if review.get("watch_stocks"):
        lines.extend(["", "## 观察名单", ""])
        for stock in review["watch_stocks"][:10]:
            lines.append(
                f"- **{stock.get('stock_name')}**（{stock.get('stock_code')}）："
                f"{stock.get('category')}，{stock.get('reason')}"
            )

    lines.extend(["", "## 涨停核心", ""])
    for stock in review["core_stocks"][:10]:
        lines.append(
            f"- {stock['stock_name']}（{stock['stock_code']}）：{stock.get('up_limit_keep_times') or 1}板，"
            f"{stock.get('primary_plate') or '-'}，{_brief_text(stock.get('reason'))}"
        )
    lines.extend(["", "## 风险点", ""])
    lines.extend([f"- {item}" for item in review["risk_flags"]])
    lines.extend(["", "## 机会观察", ""])
    lines.extend([f"- {item}" for item in review["opportunities"]])
    lines.extend(["", "## 明日计划", ""])
    lines.extend([f"- {item}" for item in review["next_plan"]])
    lines.extend(["", "---", "*报告由「发家致富」系统自动生成。*"])
    return "\n".join(lines) + "\n"


def write_markdown(review: dict[str, Any], output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{review['trade_date']}-复盘.md"
    path.write_text(render_markdown(review), encoding="utf-8")
    return path


def generate_daily_review(
    trade_date: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    if trade_date is None:
        trade_date = get_default_date(db_path)
    review = build_review_payload(trade_date, db_path)
    markdown_path = write_markdown(review, output_dir)
    review["markdown_path"] = str(markdown_path)

    db = MarketDB(db_path)
    db.init_schema()
    try:
        db.import_daily_review(review)
    finally:
        db.close()
    return review


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 A 股每日复盘结论")
    parser.add_argument("--date", help="交易日期，格式 YYYY-MM-DD；不传则使用最新交易日")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite 数据库路径")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_DIR), help="Markdown 输出目录")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = parser.parse_args()

    review = generate_daily_review(args.date, args.db, args.out)
    if args.json:
        print(json.dumps(review, ensure_ascii=False, indent=2))
    else:
        print(f"已生成复盘: {review['trade_date']}")
        print(f"报告文件: {review['markdown_path']}")
        print(review["summary"])


if __name__ == "__main__":
    main()
