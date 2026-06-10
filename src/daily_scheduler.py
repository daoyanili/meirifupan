"""Simple daily scheduler for market review updates."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_update import run_daily_update
from fetch_missing_data import DEFAULT_DB_PATH
from premarket_update import run_premarket_update


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":", 1)
    return int(hour), int(minute)


def next_run_time(run_at: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    hour, minute = _parse_hhmm(run_at)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def next_named_run_time(schedule: dict[str, str], now: datetime | None = None) -> tuple[str, datetime]:
    """Return the next task name and run time from a daily HH:MM schedule."""
    now = now or datetime.now()
    candidates = [(name, next_run_time(run_at, now)) for name, run_at in schedule.items()]
    return min(candidates, key=lambda item: item[1])


def run_scheduler(
    run_at: str,
    premarket_at: str = "08:30",
    db_path: str = DEFAULT_DB_PATH,
    kline_limit: int = 30,
    force: bool = False,
) -> None:
    schedule = {
        "premarket_update": premarket_at,
        "daily_update": run_at,
    }
    print(f"自动调度已启动: 盘前 {premarket_at}，复盘 {run_at}，数据库 {db_path}", flush=True)
    while True:
        task_name, target = next_named_run_time(schedule)
        wait_seconds = max(1, int((target - datetime.now()).total_seconds()))
        print(f"下次执行: {task_name} {target.isoformat(timespec='seconds')}", flush=True)
        time.sleep(wait_seconds)
        try:
            if task_name == "premarket_update":
                summary = run_premarket_update(db_path=db_path)
                print(f"盘前结束: {summary.get('guide_date')} {summary.get('status')} {summary.get('message')}", flush=True)
            else:
                summary = run_daily_update(db_path=db_path, kline_limit=kline_limit, force=force)
                print(f"复盘结束: {summary.get('trade_date')} {summary.get('status')} {summary.get('message')}", flush=True)
        except Exception as exc:
            print(f"更新失败: {exc}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="每日 A 股复盘数据自动更新调度器")
    parser.add_argument("--run-at", default=os.environ.get("DAILY_UPDATE_AT", "17:30"), help="每天执行时间，格式 HH:MM")
    parser.add_argument("--premarket-at", default=os.environ.get("PREMARKET_UPDATE_AT", "08:30"), help="盘前指引执行时间，格式 HH:MM")
    parser.add_argument("--db", default=os.environ.get("DB_PATH", DEFAULT_DB_PATH), help="SQLite 数据库路径")
    parser.add_argument("--kline-limit", type=int, default=int(os.environ.get("DAILY_KLINE_LIMIT", "30")))
    parser.add_argument("--force", action="store_true", default=os.environ.get("DAILY_UPDATE_FORCE") == "1")
    args = parser.parse_args()

    run_scheduler(args.run_at, args.premarket_at, args.db, args.kline_limit, args.force)


if __name__ == "__main__":
    main()
