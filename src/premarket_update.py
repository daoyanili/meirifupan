"""Pre-market guide update entry point."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MarketDB
from daily_update import compact_result, now_text
from fetch_missing_data import DEFAULT_DB_PATH
from fetch_premarket import collect_premarket_data
from generate_premarket import generate_premarket_guide


def run_premarket_update(
    guide_date: str | None = None,
    review_date: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
    strict: bool = False,
) -> dict[str, Any]:
    """Collect overnight data and generate the pre-market guide."""
    guide_date = guide_date or datetime.now().strftime("%Y-%m-%d")
    started_at = now_text()
    summary: dict[str, Any] = {
        "guide_date": guide_date,
        "review_date": review_date,
        "strict": strict,
        "steps": [],
    }

    db = MarketDB(db_path)
    db.init_schema()
    try:
        db.log_data_job("premarket_update", guide_date, "running", "开始盘前指引更新", summary, started_at, None)
    finally:
        db.close()

    def run_step(name: str, fn) -> Any:
        step_started = now_text()
        try:
            result = fn()
            summary["steps"].append({
                "name": name,
                "status": "success",
                "started_at": step_started,
                "finished_at": now_text(),
                "result": compact_result(result),
            })
            return result
        except Exception as exc:
            summary["steps"].append({
                "name": name,
                "status": "failed",
                "started_at": step_started,
                "finished_at": now_text(),
                "message": str(exc),
                "traceback": traceback.format_exc(limit=8),
            })
            if strict:
                raise
            return None

    strict_error: Exception | None = None
    try:
        collect_result = run_step(
            "采集盘前外部信息",
            lambda: collect_premarket_data(guide_date=guide_date, review_date=review_date, db_path=db_path),
        )
        if isinstance(collect_result, dict):
            summary["review_date"] = collect_result.get("review_date") or review_date
        guide = run_step(
            "生成盘前指引",
            lambda: generate_premarket_guide(guide_date=guide_date, review_date=summary.get("review_date"), db_path=db_path),
        )
        if isinstance(guide, dict):
            summary["review_date"] = guide.get("review_date") or summary.get("review_date")
            summary["headline"] = guide.get("headline")
        failed_steps = [step for step in summary["steps"] if step["status"] != "success"]
        status = "success" if not failed_steps else "partial"
        message = "盘前指引更新完成" if status == "success" else f"{len(failed_steps)} 个步骤失败，已尽量生成"
    except Exception as exc:
        strict_error = exc
        status = "failed"
        message = str(exc)
        summary["steps"].append({
            "name": "盘前指引更新",
            "status": "failed",
            "started_at": started_at,
            "finished_at": now_text(),
            "message": message,
            "traceback": traceback.format_exc(limit=8),
        })

    summary["status"] = status
    summary["message"] = message

    db = MarketDB(db_path)
    db.init_schema()
    try:
        db.log_data_job("premarket_update", guide_date, status, message, summary, started_at, now_text())
    finally:
        db.close()

    if strict_error is not None and strict:
        raise strict_error
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="盘前指引自动更新")
    parser.add_argument("--date", help="盘前指引日期，默认今天")
    parser.add_argument("--review-date", help="使用哪一天的复盘作为基础")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite 数据库路径")
    parser.add_argument("--strict", action="store_true", help="任一步失败就退出")
    args = parser.parse_args()
    summary = run_premarket_update(args.date, args.review_date, args.db, args.strict)
    print(f"{summary['guide_date']} {summary.get('status')}: {summary.get('message')}")


if __name__ == "__main__":
    main()
