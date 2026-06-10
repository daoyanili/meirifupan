"""Fetch pre-market news, announcements and US stock movers."""

from __future__ import annotations

import argparse
import os
import signal
from datetime import datetime
from typing import Any, Callable

from db import MarketDB
from fetch_missing_data import DEFAULT_DB_PATH
from generate_premarket import resolve_review_date


US_FAMOUS_SECTORS = ["科技类", "汽车能源类", "媒体类", "金融类", "医药食品类", "制造零售类"]


class TimeoutError(RuntimeError):
    pass


def _timeout_handler(signum, frame) -> None:
    raise TimeoutError("数据源响应超时")


def call_with_timeout(fn: Callable[[], Any], seconds: int = 18) -> Any:
    """Run a blocking AkShare call with a hard timeout on Unix-like systems."""
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(seconds)
    try:
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


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


def _text(value: Any) -> str | None:
    value = _clean(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _num(value: Any) -> float | None:
    value = _clean(value)
    if value in ("", "-", "--", None):
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row and not _is_blank(row.get(name)):
            return row.get(name)
    lowered = {str(k).lower(): k for k in row.keys()}
    for name in names:
        key = lowered.get(name.lower())
        if key is not None and not _is_blank(row.get(key)):
            return row.get(key)
    return None


def _records(df: Any) -> list[dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []
    return [dict(row) for row in df.to_dict(orient="records")]


def _ak_date(value: str) -> str:
    return value.replace("-", "")


def _code(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = text.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    return text


def _fallback_title(row: dict[str, Any]) -> str | None:
    for value in row.values():
        text = _text(value)
        if text and len(text) >= 6:
            return text[:120]
    return None


def fetch_news_records(guide_date: str, limit: int = 40) -> list[dict[str, Any]]:
    """Fetch overnight market news from public AkShare sources."""
    import akshare as ak

    sources: list[tuple[str, Callable[[], Any]]] = [
        ("cls", lambda: ak.stock_info_global_cls(symbol="重点")),
        ("eastmoney", ak.stock_info_global_em),
        ("sina", ak.stock_info_global_sina),
        ("cctv", lambda: ak.news_cctv(date=_ak_date(guide_date))),
    ]
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source, fn in sources:
        try:
            rows = _records(call_with_timeout(fn))
        except Exception as exc:
            print(f"  ⚠️  新闻源 {source} 失败: {exc}")
            continue
        for row in rows:
            title = _text(_first(row, ["标题", "title", "新闻标题", "内容", "摘要"])) or _fallback_title(row)
            if not title:
                continue
            key = title[:80]
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "source": source,
                "published_at": _text(_first(row, ["发布时间", "时间", "日期", "date", "datetime"])),
                "title": title,
                "content": _text(_first(row, ["内容", "摘要", "简介", "summary"])),
                "url": _text(_first(row, ["链接", "url", "新闻链接"])),
                "raw_payload": row,
            })
            if len(records) >= limit:
                return records
    return records


def fetch_announcement_records(notice_date: str, limit: int = 60) -> list[dict[str, Any]]:
    """Fetch A-share announcements for the review date."""
    import akshare as ak

    try:
        rows = _records(call_with_timeout(lambda: ak.stock_notice_report(symbol="全部", date=_ak_date(notice_date)), 22))
    except Exception as exc:
        print(f"  ⚠️  公告源失败: {exc}")
        return []
    records: list[dict[str, Any]] = []
    for row in rows[:limit]:
        title = _text(_first(row, ["公告标题", "标题", "notice_title", "title"])) or _fallback_title(row)
        if not title:
            continue
        records.append({
            "stock_code": _code(_first(row, ["代码", "股票代码", "证券代码", "stock_code"])),
            "stock_name": _text(_first(row, ["名称", "股票简称", "证券简称", "stock_name"])),
            "notice_date": notice_date,
            "notice_type": _text(_first(row, ["公告类型", "类型", "notice_type"])),
            "title": title,
            "url": _text(_first(row, ["公告链接", "链接", "url"])),
            "raw_payload": row,
        })
    return records


def fetch_us_stock_records(quote_date: str, limit: int = 60) -> list[dict[str, Any]]:
    """Fetch famous US stock movers for overnight reference."""
    import akshare as ak

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sector in US_FAMOUS_SECTORS:
        try:
            rows = _records(call_with_timeout(lambda sector=sector: ak.stock_us_famous_spot_em(symbol=sector), 18))
        except Exception as exc:
            print(f"  ⚠️  美股源 {sector} 失败: {exc}")
            continue
        for row in rows:
            symbol = _text(_first(row, ["代码", "symbol", "编码"]))
            if not symbol:
                continue
            symbol = symbol.replace(".O", "").replace(".N", "").upper()
            if symbol in seen:
                continue
            seen.add(symbol)
            records.append({
                "symbol": symbol,
                "stock_name": _text(_first(row, ["名称", "股票名称", "中文名称", "name"])) or symbol,
                "sector": sector,
                "latest_price": _num(_first(row, ["最新价", "价格", "price", "最新"])),
                "change_pct": _num(_first(row, ["涨跌幅", "涨幅", "change_pct", "percent"])),
                "change_amount": _num(_first(row, ["涨跌额", "change_amount", "涨跌"])),
                "raw_payload": row,
            })
    records.sort(key=lambda item: abs(item.get("change_pct") or 0), reverse=True)
    return records[:limit]


def collect_premarket_data(
    guide_date: str | None = None,
    review_date: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, int | str]:
    """Fetch and store pre-market external data."""
    guide_date = guide_date or datetime.now().strftime("%Y-%m-%d")
    db = MarketDB(db_path)
    db.init_schema()
    try:
        resolved_review_date = resolve_review_date(db.conn, guide_date, review_date)
        news = fetch_news_records(guide_date)
        announcements = fetch_announcement_records(resolved_review_date)
        us_quotes = fetch_us_stock_records(guide_date)
        return {
            "guide_date": guide_date,
            "review_date": resolved_review_date,
            "news": db.import_premarket_news(guide_date, news),
            "announcements": db.import_stock_announcements(resolved_review_date, announcements),
            "us_quotes": db.import_us_stock_quotes(guide_date, us_quotes),
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="采集盘前新闻、公告和隔夜美股")
    parser.add_argument("--date", help="盘前指引日期，默认今天")
    parser.add_argument("--review-date", help="公告对应的上一交易日")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite 数据库路径")
    args = parser.parse_args()
    result = collect_premarket_data(args.date, args.review_date, args.db)
    print(result)


if __name__ == "__main__":
    main()
