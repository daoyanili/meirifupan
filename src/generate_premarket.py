"""Generate pre-market guidance from yesterday review and overnight catalysts."""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from db import MarketDB
from fetch_missing_data import DEFAULT_DB_PATH


AI_KEYWORDS = ("AI", "算力", "服务器", "英伟达", "NVDA", "芯片", "半导体", "存储", "光模块", "CPO")
ROBOT_KEYWORDS = ("机器人", "特斯拉", "自动驾驶", "工业母机")
AUTO_KEYWORDS = ("汽车", "新能源车", "锂电", "固态电池", "储能")
CONSUMER_KEYWORDS = ("消费", "食品", "旅游", "零售", "白酒")
FINANCE_KEYWORDS = ("金融", "券商", "银行", "保险")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [_row_to_dict(row) for row in rows]


def _pct_text(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.2f}%"


def _amount_text(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{round(float(value) / 100000000):,}亿"


def _infer_theme(text: str) -> str | None:
    upper = text.upper()
    groups = [
        ("AI算力", AI_KEYWORDS),
        ("机器人", ROBOT_KEYWORDS),
        ("新能源车", AUTO_KEYWORDS),
        ("消费", CONSUMER_KEYWORDS),
        ("金融", FINANCE_KEYWORDS),
    ]
    for theme, keywords in groups:
        if any(keyword.upper() in upper for keyword in keywords):
            return theme
    return None


def resolve_review_date(conn: sqlite3.Connection, guide_date: str, review_date: str | None = None) -> str:
    if review_date:
        return review_date
    row = conn.execute(
        """
        select max(trade_date) as trade_date
        from limit_up_events
        where trade_date < ?
        """,
        (guide_date,),
    ).fetchone()
    if row and row["trade_date"]:
        return row["trade_date"]
    row = conn.execute(
        """
        select max(trade_date) as trade_date
        from daily_reviews
        where trade_date < ?
        """,
        (guide_date,),
    ).fetchone()
    if row and row["trade_date"]:
        return row["trade_date"]
    raise RuntimeError(f"{guide_date} 之前没有可用复盘数据")


def _market_row(conn: sqlite3.Connection, review_date: str) -> dict[str, Any]:
    row = conn.execute(
        """
        select total_count, up_count, down_count, flat_count, limit_up_count,
               limit_down_count, natural_limit_up_count, natural_limit_down_count,
               avg_change_pct, amount
        from market_breadth_daily
        where trade_date = ?
        """,
        (review_date,),
    ).fetchone()
    return _row_to_dict(row) if row else {}


def _focus_plates(conn: sqlite3.Connection, review_date: str, limit: int = 6) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select h.board_code, h.board_name, h.rank_no, h.change_pct, h.up_count,
               h.down_count, h.leading_stock,
               (
                   select count(*)
                   from limit_up_plate_map m
                   where m.trade_date = h.trade_date and m.plate_code = h.board_code
               ) as limit_up_count
        from hot_boards h
        where h.trade_date = ? and h.board_type = 'concept'
        order by h.rank_no asc
        limit ?
        """,
        (review_date, limit),
    ).fetchall()
    result = []
    for row in rows:
        item = _row_to_dict(row)
        item["plate_code"] = item.get("board_code")
        item["plate_name"] = item.get("board_name")
        item["reason"] = f"昨日板块排名第 {item['rank_no']}，涨幅 {_pct_text(item.get('change_pct'))}，涨停 {item.get('limit_up_count') or 0} 只。"
        result.append(item)
    if result:
        return result

    rows = conn.execute(
        """
        select m.plate_code as board_code, m.plate_name as board_name,
               count(distinct m.stock_code) as limit_up_count,
               max(e.up_limit_keep_times) as highest_board,
               null as rank_no, null as change_pct, null as up_count,
               null as down_count, null as leading_stock
        from limit_up_plate_map m
        left join limit_up_events e
          on e.trade_date = m.trade_date and e.stock_code = m.stock_code
        where m.trade_date = ?
        group by m.plate_code, m.plate_name
        order by limit_up_count desc, highest_board desc
        limit ?
        """,
        (review_date, limit),
    ).fetchall()
    result = []
    for row in rows:
        item = _row_to_dict(row)
        item["plate_code"] = item.get("board_code")
        item["plate_name"] = item.get("board_name")
        item["reason"] = f"昨日涨停 {item.get('limit_up_count') or 0} 只，最高 {item.get('highest_board') or '-'} 板。"
        result.append(item)
    if result:
        return result

    rows = conn.execute(
        """
        select plate_code as board_code, plate_name as board_name, rank_no, score,
               null as change_pct, null as up_count, null as down_count,
               null as leading_stock,
               (
                   select count(*)
                   from limit_up_plate_map m
                   where m.trade_date = p.trade_date and m.plate_code = p.plate_code
               ) as limit_up_count
        from plate_hot_rank p
        where p.trade_date = ?
        order by rank_no asc
        limit ?
        """,
        (review_date, limit),
    ).fetchall()
    return [
        {
            **_row_to_dict(row),
            "plate_code": row["board_code"],
            "plate_name": row["board_name"],
            "reason": f"昨日涨停热度靠前，涨停 {row['limit_up_count'] or 0} 只。",
        }
        for row in rows
    ]


def _hot_stocks(conn: sqlite3.Connection, review_date: str, limit: int = 8) -> list[dict[str, Any]]:
    source_row = conn.execute(
        """
        select count(*) as total
        from hot_stocks
        where trade_date = ? and source like 'eastmoney%'
        """,
        (review_date,),
    ).fetchone()
    source_filter = "source like 'eastmoney%'" if source_row and source_row["total"] else "1 = 1"
    return _rows(conn.execute(
        f"""
        select rank_no, stock_code, stock_name, latest_price, change_pct, amount, turnover_rate, source
        from hot_stocks
        where trade_date = ? and {source_filter}
        order by rank_no asc
        limit ?
        """,
        (review_date, limit),
    ).fetchall())


def _space_stocks(conn: sqlite3.Connection, review_date: str, limit: int = 5) -> list[dict[str, Any]]:
    return _rows(conn.execute(
        """
        select stock_code, stock_name, up_limit_keep_times, up_limit_desc,
               up_limit_time, reason, fengdan_money, fengdan_rate
        from limit_up_events
        where trade_date = ?
        order by up_limit_keep_times desc, up_limit_time asc
        limit ?
        """,
        (review_date, limit),
    ).fetchall())


def _news(conn: sqlite3.Connection, guide_date: str, limit: int = 12) -> list[dict[str, Any]]:
    return _rows(conn.execute(
        """
        select source, published_at, title, content, url
        from premarket_news
        where guide_date = ?
        order by coalesce(published_at, '') desc
        limit ?
        """,
        (guide_date, limit),
    ).fetchall())


def _announcements(conn: sqlite3.Connection, notice_date: str, limit: int = 12) -> list[dict[str, Any]]:
    return _rows(conn.execute(
        """
        select stock_code, stock_name, notice_date, notice_type, title, url
        from stock_announcements
        where notice_date = ?
        order by stock_code is null, stock_code, title
        limit ?
        """,
        (notice_date, limit),
    ).fetchall())


def _us_markets(conn: sqlite3.Connection, guide_date: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = _rows(conn.execute(
        """
        select symbol, stock_name, sector, latest_price, change_pct, change_amount
        from us_stock_quotes
        where quote_date = ?
        order by abs(coalesce(change_pct, 0)) desc
        limit ?
        """,
        (guide_date, limit),
    ).fetchall())
    for item in rows:
        text = f"{item.get('symbol', '')} {item.get('stock_name', '')} {item.get('sector', '')}"
        item["mapped_theme"] = _infer_theme(text)
    return rows


def _build_market_tone(market: dict[str, Any]) -> str:
    if not market:
        return "缺少昨日大盘广度数据，先按复盘强弱和隔夜消息做观察。"
    up_count = market.get("up_count") or 0
    down_count = market.get("down_count") or 0
    limit_up = market.get("limit_up_count") or 0
    limit_down = market.get("limit_down_count") or 0
    amount = _amount_text(market.get("amount"))
    avg = _pct_text(market.get("avg_change_pct"))
    if limit_down >= max(8, limit_up * 0.4):
        return f"昨日成交额 {amount}，平均涨幅 {avg}，但跌停 {limit_down} 只，早盘先看风险释放。"
    if up_count > down_count and limit_up >= 50:
        return f"昨日成交额 {amount}，上涨家数多于下跌家数，涨停 {limit_up} 只，情绪有修复基础。"
    return f"昨日成交额 {amount}，平均涨幅 {avg}，涨停 {limit_up} 只、跌停 {limit_down} 只，先看主线能否继续聚焦。"


def _build_watch_points(
    focus_plates: list[dict[str, Any]],
    hot_stocks: list[dict[str, Any]],
    space_stocks: list[dict[str, Any]],
    news: list[dict[str, Any]],
    announcements: list[dict[str, Any]],
    us_markets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    top_plate = focus_plates[0] if focus_plates else None
    if top_plate:
        points.append({
            "title": f"主线延续：{top_plate.get('plate_name') or top_plate.get('board_name')}",
            "reason": top_plate.get("reason") or "昨日板块热度靠前。",
            "trigger": "开盘后看板块前排是否继续高开并有换手承接。",
        })
    if space_stocks:
        stock = space_stocks[0]
        points.append({
            "title": f"空间板反馈：{stock.get('stock_name')}",
            "reason": f"昨日最高连板为 {stock.get('up_limit_desc') or str(stock.get('up_limit_keep_times')) + '板'}，它决定短线高度能不能继续打开。",
            "trigger": "如果高位股低开后快速走弱，先降低连板接力预期。",
        })
    if hot_stocks:
        names = "、".join(item.get("stock_name") or item.get("stock_code") for item in hot_stocks[:3])
        points.append({
            "title": "人气股承接",
            "reason": f"昨日人气前排是 {names}，这些不一定都涨停，但更能反映资金关注。",
            "trigger": "看前排人气股是否比普通涨停股更强，决定今天是看趋势还是看连板。",
        })
    mapped = [item for item in us_markets if item.get("mapped_theme") and (item.get("change_pct") or 0) > 1]
    if mapped:
        item = mapped[0]
        points.append({
            "title": f"隔夜美股映射：{item.get('mapped_theme')}",
            "reason": f"{item.get('stock_name') or item.get('symbol')} 隔夜涨幅 {_pct_text(item.get('change_pct'))}，美股强势可能给 A 股相关方向提供早盘催化。",
            "trigger": "只看竞价和开盘 15 分钟是否兑现到 A 股核心股，不追单一消息。",
        })
    important_notice = announcements[0] if announcements else None
    if important_notice:
        points.append({
            "title": f"公告催化：{important_notice.get('stock_name') or important_notice.get('stock_code') or '重点公告'}",
            "reason": important_notice.get("title") or "昨晚有重点公告。",
            "trigger": "先看公告股是否带动同板块，不只看单只高开。",
        })
    important_news = news[0] if news else None
    if important_news and not mapped:
        points.append({
            "title": "新闻催化",
            "reason": important_news.get("title") or "隔夜有重点消息。",
            "trigger": "消息要落到板块和核心股强弱上，弱兑现就不硬做。",
        })
    return points[:6]


def _build_risk_points(market: dict[str, Any], us_markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    limit_down = market.get("limit_down_count") if market else None
    avg = market.get("avg_change_pct") if market else None
    if limit_down is not None and limit_down >= 8:
        risks.append({
            "title": "亏钱反馈没有完全消失",
            "reason": f"昨日跌停 {limit_down} 只，早盘如果高位股继续补跌，先防守。",
        })
    if avg is not None and avg < -0.5:
        risks.append({
            "title": "市场平均涨幅偏弱",
            "reason": f"昨日全市场平均涨幅 {_pct_text(avg)}，说明赚钱效应没有扩散。",
        })
    weak_us = [item for item in us_markets if (item.get("change_pct") or 0) <= -2]
    if weak_us:
        item = weak_us[0]
        risks.append({
            "title": "隔夜外盘拖累",
            "reason": f"{item.get('stock_name') or item.get('symbol')} 跌幅 {_pct_text(item.get('change_pct'))}，相关映射方向早盘容易先分歧。",
        })
    if not risks:
        risks.append({
            "title": "不要只因为消息追高",
            "reason": "盘前消息只决定观察方向，真正能不能做要看开盘承接和板块合力。",
        })
    return risks[:4]


def _build_headline(focus_plates: list[dict[str, Any]], us_markets: list[dict[str, Any]], market_tone: str) -> str:
    plate = (focus_plates[0].get("plate_name") or focus_plates[0].get("board_name")) if focus_plates else "昨日主线"
    mapped = next((item for item in us_markets if item.get("mapped_theme") and (item.get("change_pct") or 0) > 1), None)
    if mapped:
        return f"盘前先看 {plate}，隔夜{mapped.get('stock_name') or mapped.get('symbol')}强化{mapped.get('mapped_theme')}线索"
    if "风险" in market_tone or "跌停" in market_tone:
        return f"盘前先看 {plate} 的修复力度，同时防高位分歧"
    return f"盘前先看 {plate} 能否从昨日强势延续到早盘承接"


def generate_premarket_guide(
    guide_date: str | None = None,
    review_date: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    guide_date = guide_date or datetime.now().strftime("%Y-%m-%d")
    db = MarketDB(db_path)
    db.init_schema()
    try:
        conn = db.conn
        resolved_review_date = resolve_review_date(conn, guide_date, review_date)
        market = _market_row(conn, resolved_review_date)
        focus_plates = _focus_plates(conn, resolved_review_date)
        hot_stocks = _hot_stocks(conn, resolved_review_date)
        space_stocks = _space_stocks(conn, resolved_review_date)
        news = _news(conn, guide_date)
        announcements = _announcements(conn, resolved_review_date)
        us_markets = _us_markets(conn, guide_date)
        market_tone = _build_market_tone(market)
        watch_points = _build_watch_points(
            focus_plates,
            hot_stocks,
            space_stocks,
            news,
            announcements,
            us_markets,
        )
        risk_points = _build_risk_points(market, us_markets)
        guide = {
            "guide_date": guide_date,
            "review_date": resolved_review_date,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "headline": _build_headline(focus_plates, us_markets, market_tone),
            "market_tone": market_tone,
            "market_snapshot": market,
            "focus_plates": focus_plates,
            "hot_stocks": hot_stocks,
            "space_stocks": space_stocks,
            "watch_points": watch_points,
            "risk_points": risk_points,
            "catalyst_news": news,
            "announcements": announcements,
            "us_markets": us_markets,
        }
        db.import_premarket_guide(guide)
        return guide
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="生成盘前指引")
    parser.add_argument("--date", help="盘前指引日期，默认今天")
    parser.add_argument("--review-date", help="使用哪一天的复盘作为基础，默认取上一交易日")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite 数据库路径")
    args = parser.parse_args()
    guide = generate_premarket_guide(args.date, args.review_date, args.db)
    print(f"{guide['guide_date']} 盘前指引已生成: {guide['headline']}")


if __name__ == "__main__":
    main()
